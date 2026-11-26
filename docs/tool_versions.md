# Tool versions (recorded 2026-11-26 on the Member A machine; CI uses ubuntu-24.04 + the same lock files)

| Tool | Version | Used for |
|---|---|---|
| OS | Linux 7.3.5-2-cachyos (CachyOS) | local runs |
| Python | 3.12.16 (uv-managed) | SUT + all Python tooling |
| uv | 0.13.10 | Python install / venv |
| Django | 4.2.30 | system under test |
| pytest | 8.3.5 | unit, API, integration |
| pytest-django | 4.11.1 | Django test DB + live server |
| pytest-cov | 6.1.1 | coverage integration |
| coverage.py | 7.8.0 | statement + branch coverage |
| Requests | 2.32.3 | API test client |
| PyYAML | 6.0.2 | reading the OpenAPI spec |
| openapi-spec-validator | 0.7.1 | spec validation |
| Cosmic Ray | 8.4.1 | mutation testing |
| pip-audit | 2.9.0 | dependency audit |
| gunicorn | 23.0.0 | server for performance runs |
| matplotlib | 3.10.1 | figures |
| pysonar (SonarScanner for Python) | 1.11.0.6012 | Sonar analysis |
| Node.js | v26.13.1 | Playwright runner |
| @playwright/test | 1.52.0 | browser E2E |
| Chromium (Playwright build 1169) | 136.0.7103.25 | browser |
| @axe-core/playwright | 4.10.1 (axe-core 4.10.3) | accessibility scan |
| Lighthouse | 12.6.0 | accessibility / best practices / SEO |
| SonarQube Community Build | 26.11.0.134175 (Docker sonarqube:community) | static analysis |
| Grafana k6 | v1.0.0 | load tests |
| OWASP ZAP | 2.16.1 (cross-platform package, Java 27.0.1.1) | passive scan |
| Docker | 29.10.0 | SonarQube |
| GitHub CLI | 2.105.0 | issues, PRs |
