import type { Env } from "../env";

export interface CreatedIssue {
  number: number;
  url: string;
}

export async function createIssue(
  env: Env,
  args: { repo?: string; title: string; body: string; labels?: string[] },
): Promise<CreatedIssue> {
  const repo = args.repo ?? env.DEFAULT_GH_REPO;
  const res = await fetch(`https://api.github.com/repos/${repo}/issues`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${env.GITHUB_TOKEN}`,
      accept: "application/vnd.github+json",
      "user-agent": "triage-worker",
    },
    body: JSON.stringify({ title: args.title, body: args.body, labels: args.labels }),
  });
  if (!res.ok) throw new Error(`github issue failed: ${res.status} ${await res.text()}`);
  const data = (await res.json()) as { number: number; html_url: string };
  return { number: data.number, url: data.html_url };
}
