// Doc section 5 - load test of ONE operation used by WF1:  GET /requisition/{pk}/hod-approval/
//   (the HOD's approval screen: auth + department-scoped query + line items with live stock).
//
//   k6 run -e VUS=1 -e PK=1 --summary-export results/<run>.json tests/team/perf/approval_screen.js
//
// Two scenarios with the SAME number of VUs:
//   warmup   0-15 s   (VUs log in, caches warm; not measured)
//   measured 15-85 s  (70 s, all N users already running -> >= 60 s measured at full load)
// Targets were fixed BEFORE the first run (docs/18_performance.md) and are enforced as thresholds.
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

const BASE = __ENV.BASE_URL || 'http://127.0.0.1:8000';
const VUS = Number(__ENV.VUS || 1);
const PK = __ENV.PK || '1';
const USER = __ENV.USER_NAME || 'hod_it';
const PASSWORD = __ENV.PASSWORD || 'Test@12345';
const P95_LIMIT = VUS === 1 ? 300 : 800;          // ms - see docs/18_performance.md

const approvalTime = new Trend('approval_screen_ms', true);
const unexpected = new Rate('unexpected_failures');
const completed = new Counter('approval_requests');

export const options = {
  scenarios: {
    warmup:   { executor: 'constant-vus', vus: VUS, duration: '15s', tags: { phase: 'warmup' } },
    measured: { executor: 'constant-vus', vus: VUS, duration: '70s', startTime: '15s', tags: { phase: 'measured' } },
  },
  thresholds: {
    'approval_screen_ms{phase:measured}': [`p(95)<=${P95_LIMIT}`],
    'unexpected_failures{phase:measured}': ['rate<0.01'],
    'approval_requests{phase:measured}': ['count>0'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'max'],
  noCookiesReset: true,            // keep each VU's session cookie across iterations (k6 resets it by default)
};

function login() {
  const page = http.get(`${BASE}/login/`, { tags: { name: 'login' } });
  const token = page.cookies.csrftoken ? page.cookies.csrftoken[0].value : '';
  const res = http.post(`${BASE}/login/`, { username: USER, password: PASSWORD, csrfmiddlewaretoken: token },
                        { redirects: 0, tags: { name: 'login' }, headers: { Referer: `${BASE}/login/` } });
  check(res, { 'login redirected': r => r.status === 302 });
}

export default function () {
  if (__ITER === 0) login();                       // each VU keeps its own cookie jar (session)
  const res = http.get(`${BASE}/requisition/${PK}/hod-approval/`, { tags: { name: 'approval' }, redirects: 0 });
  const ok = check(res, {
    'status 200': r => r.status === 200,
    'decision form rendered': r => r.body && r.body.includes('Submit Decision'),
  });
  unexpected.add(!ok);
  approvalTime.add(res.timings.duration);
  completed.add(1);
  sleep(1);                                        // think time: one screen view per second per user
}
