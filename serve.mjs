import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.dirname(fileURLToPath(import.meta.url));
const site = process.argv[2];

if (!site) {
  const sitesDir = path.join(repoRoot, "sites");
  const available = fs.existsSync(sitesDir) ? fs.readdirSync(sitesDir) : [];
  console.error("Usage: node serve.mjs sites/<site-name>");
  if (available.length) console.error(`Available sites: ${available.join(", ")}`);
  process.exit(1);
}

const root = path.resolve(repoRoot, site);
if (!fs.existsSync(path.join(root, "index.html"))) {
  console.error(`No index.html found in ${root}`);
  process.exit(1);
}

const port = 3000;

const mime = {
  ".html": "text/html",
  ".css": "text/css",
  ".js": "text/javascript",
  ".mjs": "text/javascript",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
};

http
  .createServer((req, res) => {
    let urlPath = decodeURIComponent(req.url.split("?")[0]);
    if (urlPath === "/") urlPath = "/index.html";
    const filePath = path.join(root, urlPath);

    if (!filePath.startsWith(root)) {
      res.writeHead(403);
      res.end("Forbidden");
      return;
    }

    fs.readFile(filePath, (err, data) => {
      if (err) {
        res.writeHead(404, { "Content-Type": "text/plain" });
        res.end("Not found");
        return;
      }
      const ext = path.extname(filePath);
      res.writeHead(200, { "Content-Type": mime[ext] || "application/octet-stream" });
      res.end(data);
    });
  })
  .listen(port, () => {
    console.log(`Serving ${root} at http://localhost:${port}`);
  });
