const http = require("http");
const { URL } = require("url");

let prompts = [];
let idCounter = 1;

const sendJson = (res, status, payload) => {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(payload));
};

const parseBody = (req) =>
  new Promise((resolve, reject) => {
    let data = "";
    req.on("data", (chunk) => {
      data += chunk;
    });
    req.on("end", () => {
      if (!data) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(data));
      } catch (error) {
        reject(error);
      }
    });
    req.on("error", reject);
  });

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost:8000");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader(
    "Access-Control-Allow-Headers",
    "Content-Type, X-Actor-Id, X-Actor-Roles, X-Tenant-Id"
  );
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS");
  if (req.method === "OPTIONS") {
    res.writeHead(204);
    res.end();
    return;
  }

  if (!url.pathname.startsWith("/api/prompts")) {
    sendJson(res, 404, { error: "Not Found" });
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/prompts") {
    sendJson(res, 200, {
      data: {
        items: prompts,
        page: 1,
        pageSize: 50,
      },
      meta: {
        total: prompts.length,
      },
    });
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/prompts") {
    try {
      const body = await parseBody(req);
      const name = (body.name || "").trim();
      const markdown = (body.markdown || "").trim();
      if (!name || !markdown) {
        sendJson(res, 400, { error: "名称或内容不能为空" });
        return;
      }
      const now = new Date().toISOString();
      const prompt = {
        id: String(idCounter++),
        name,
        markdown,
        createdAt: now,
        updatedAt: now,
      };
      prompts = [prompt, ...prompts];
      sendJson(res, 201, { data: prompt });
    } catch (error) {
      sendJson(res, 500, { error: error.message });
    }
    return;
  }

  const match = url.pathname.match(/\/api\/prompts\/(.+)/);
  if (!match) {
    sendJson(res, 404, { error: "Not Found" });
    return;
  }
  const promptId = match[1];
  const index = prompts.findIndex((item) => item.id === promptId);
  if (index === -1) {
    sendJson(res, 404, { error: "Prompt Not Found" });
    return;
  }

  if (req.method === "PUT") {
    try {
      const body = await parseBody(req);
      const updated = { ...prompts[index] };
      if (body.name !== undefined) {
        const nextName = (body.name || "").trim();
        if (!nextName) {
          sendJson(res, 400, { error: "名称不能为空" });
          return;
        }
        updated.name = nextName;
      }
      if (body.markdown !== undefined) {
        const nextMarkdown = (body.markdown || "").trim();
        if (!nextMarkdown) {
          sendJson(res, 400, { error: "Markdown 不能为空" });
          return;
        }
        updated.markdown = nextMarkdown;
      }
      updated.updatedAt = new Date().toISOString();
      prompts[index] = updated;
      sendJson(res, 200, { data: updated });
    } catch (error) {
      sendJson(res, 500, { error: error.message });
    }
    return;
  }

  if (req.method === "DELETE") {
    prompts.splice(index, 1);
    sendJson(res, 200, { meta: { success: true } });
    return;
  }

  sendJson(res, 405, { error: "Method Not Allowed" });
});

server.listen(8000, () => {
  console.log("Mock API listening on http://localhost:8000");
});
