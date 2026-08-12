const { spawnSync } = require("node:child_process");

const env = {
  ...process.env,
  NEXT_PUBLIC_API_URL:
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api/v1",
  // This value is only used while statically compiling the app. Runtime auth
  // still requires a real NEXTAUTH_SECRET in non-development environments.
  NEXTAUTH_SECRET: process.env.NEXTAUTH_SECRET || "build-only-secret",
};

const nextBin = require.resolve("next/dist/bin/next");
const result = spawnSync(process.execPath, [nextBin, "build", "--no-lint"], {
  stdio: "inherit",
  env,
});

process.exit(result.status ?? 1);
