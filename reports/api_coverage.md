# API coverage criteria (674 recorded calls)

| Criterion | Covered / reachable | % of reachable | Not covered | Blocked by an open defect (documented in x-observed) |
|---|---|---|---|---|
| Path coverage | 9/9 (+0 blocked) | 100.0% | - | - |
| Operation coverage | 11/11 (+0 blocked) | 100.0% | - | - |
| Parameter coverage | 22/22 (+0 blocked) | 100.0% | - | - |
| Parameter-value coverage (enums) | 14/14 (+0 blocked) | 100.0% | - | - |
| Request content-type coverage | 5/5 (+0 blocked) | 100.0% | - | - |
| Status-code class coverage | 23/23 (+0 blocked) | 100.0% | - | - |
| Status-code coverage | 25/25 (+3 blocked) | 100.0% | - | (('GET', '/requisition/{pk}/issue/'), '403'); (('POST', '/requisition/{pk}/api/update/'), '404'); (('POST', '/requisition/{pk}/issue/'), '403') |
| Response body-property coverage | 28/28 (+0 blocked) | 100.0% | - | - |
| Response content-type coverage | 7/7 (+0 blocked) | 100.0% | - | - |

'Blocked' = an expected response documented in the spec that the baseline cannot return because of an open defect (e.g. 403 for a non-Admin issue - F3). The tests for it exist and are xfail(strict); the criterion becomes coverable when the defect is fixed.
