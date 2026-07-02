import { createServer } from "node:http";
import { extname, join, normalize } from "node:path";
import { readFile, stat } from "node:fs/promises";

const root = join(process.cwd(), "dist");
const host = process.env.HOST ?? "127.0.0.1";
const port = Number(process.env.PORT ?? 3000);

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".webp": "image/webp"
};

function resolveRequestPath(url) {
  const pathname = decodeURIComponent(new URL(url, `http://${host}:${port}`).pathname);
  const normalized = normalize(pathname).replace(/^([/\\])+/, "");
  return join(root, normalized || "index.html");
}

async function readStaticFile(pathname) {
  try {
    const info = await stat(pathname);
    if (info.isDirectory()) {
      return readStaticFile(join(pathname, "index.html"));
    }
    return {
      body: await readFile(pathname),
      type: contentTypes[extname(pathname)] ?? "application/octet-stream"
    };
  } catch {
    return {
      body: await readFile(join(root, "index.html")),
      type: "text/html; charset=utf-8"
    };
  }
}

createServer(async (request, response) => {
  try {
    const file = await readStaticFile(resolveRequestPath(request.url ?? "/"));
    response.writeHead(200, { "Content-Type": file.type });
    response.end(file.body);
  } catch (error) {
    response.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
    response.end(error instanceof Error ? error.message : "Internal Server Error");
  }
}).listen(port, host, () => {
  console.log(`Frontend preview ready at http://${host}:${port}/`);
});
