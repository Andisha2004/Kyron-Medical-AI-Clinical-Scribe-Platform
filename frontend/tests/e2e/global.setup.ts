import { clearPreparedDemoData, prepareDemoData } from "./support/backend";

async function globalSetup(): Promise<void> {
  clearPreparedDemoData();
  prepareDemoData();
}

export default globalSetup;
