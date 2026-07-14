import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const projectRoot = path.resolve(__dirname, "../../..");
const backendRoot = path.resolve(projectRoot, "../backend");
const backendPython = path.resolve(backendRoot, ".venv/bin/python");
const bootstrapScript = path.resolve(backendRoot, "scripts/bootstrap_demo_database.py");
const seedScript = path.resolve(backendRoot, "scripts/seed_demo.py");
const bootstrapMarker = path.resolve(projectRoot, ".playwright/demo-data-ready");

let prepared = false;

export function clearPreparedDemoData(): void {
  prepared = false;
  if (fs.existsSync(bootstrapMarker)) {
    fs.unlinkSync(bootstrapMarker);
  }
}

export function prepareDemoData(options: { force?: boolean } = {}): void {
  if (options.force) {
    clearPreparedDemoData();
  }

  if (prepared || fs.existsSync(bootstrapMarker)) {
    prepared = true;
    return;
  }

  execFileSync(backendPython, [bootstrapScript], {
    cwd: backendRoot,
    stdio: "inherit",
  });

  execFileSync(backendPython, [seedScript], {
    cwd: backendRoot,
    stdio: "inherit",
  });

  fs.mkdirSync(path.dirname(bootstrapMarker), { recursive: true });
  fs.writeFileSync(bootstrapMarker, "ready\n", "utf8");
  prepared = true;
}
