import type { Env } from "../env";

export interface CreatedTask {
  id: string;
  url: string;
}

export async function createTask(
  env: Env,
  args: { content: string; description?: string; priority?: 1 | 2 | 3 | 4; dueString?: string },
): Promise<CreatedTask> {
  const res = await fetch("https://api.todoist.com/rest/v2/tasks", {
    method: "POST",
    headers: {
      authorization: `Bearer ${env.TODOIST_TOKEN}`,
      "content-type": "application/json",
    },
    body: JSON.stringify({
      content: args.content,
      description: args.description,
      priority: args.priority,
      due_string: args.dueString,
    }),
  });
  if (!res.ok) throw new Error(`todoist create failed: ${res.status} ${await res.text()}`);
  const data = (await res.json()) as { id: string; url: string };
  return { id: data.id, url: data.url };
}
