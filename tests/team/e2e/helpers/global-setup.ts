import { execFileSync } from 'child_process';
import path from 'path';

/** Build the seeded golden DB once per run (migrate + deterministic seed). */
export default async function globalSetup() {
  const root = path.resolve(__dirname, '../../../..');
  const py = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  execFileSync(py, [path.join(root, 'scripts/team/reset_db.py')], { cwd: root, stdio: 'inherit' });
  execFileSync(py, [path.join(__dirname, 'db_state.py'), 'reset'], { cwd: root });
}
