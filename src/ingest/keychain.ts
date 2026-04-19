import { spawn } from "node:child_process";

export interface KeychainCredential {
  service: string;
  account: string;
}

export async function getInternetPassword(cred: KeychainCredential): Promise<string> {
  return new Promise((resolve, reject) => {
    const proc = spawn("security", [
      "find-internet-password",
      "-s",
      cred.service,
      "-a",
      cred.account,
      "-w",
    ]);

    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (chunk: Buffer) => (stdout += chunk.toString()));
    proc.stderr.on("data", (chunk: Buffer) => (stderr += chunk.toString()));

    proc.on("close", (code) => {
      if (code !== 0) {
        reject(
          new Error(
            `security find-internet-password failed (exit ${code}): ${stderr.trim() || "no stderr"}`,
          ),
        );
        return;
      }
      const password = stdout.replace(/\n$/, "");
      if (!password) {
        reject(new Error("Keychain returned empty password"));
        return;
      }
      resolve(password);
    });

    proc.on("error", reject);
  });
}
