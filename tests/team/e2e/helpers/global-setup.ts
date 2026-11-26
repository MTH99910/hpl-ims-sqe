import { execFileSync } from 'child_process';
import path from 'path';

/** Build the seeded golden DB once per run (migrate + deterministic seed). */
export default async function globalSetup() {
  const root = path.resolve(__dirname, '../../../..');
  execFileSync(path.join(root, 'scripts/team/reset_db.sh'), { cwd: root, stdio: 'inherit' });
  execFileSync(path.join(root, '.venv/bin/python'), [path.join(__dirname, 'db_state.py'), 'reset'], { cwd: root });
}
