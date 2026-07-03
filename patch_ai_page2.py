import sys

with open(sys.argv[1], "r") as f:
    content = f.read()

idx = content.find("async function ask()")
if idx < 0:
    print("ERROR: Cannot find ask() function")
    sys.exit(1)

end_idx = content.find("function appendMsg", idx)
if end_idx < 0:
    end_idx = content.find("</script>", idx)

actual_block = content[idx:end_idx]
print(f"Found ask() at {idx}, block length: {len(actual_block)}")

new_ask = """async function ask() {
  const msg = input.value.trim();
  if (!msg) return;
  input.value = "";
  appendMsg("user", msg);

  const resultDiv = document.createElement("div");
  resultDiv.className = "msg bot";
  resultDiv.innerHTML = "<span class=\\"label\\">小智</span><div class=\\"stream-content\\" style=\\"display:inline;\\"></div>";
  chat.appendChild(resultDiv);
  const contentDiv = resultDiv.querySelector(".stream-content");

  sendBtn.disabled = true;

  try {
    const resp = await fetch("/api/v1/agent/stream", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({task: msg, session_id: sessionId})
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let full = "";

    while (true) {
      const {done, value} = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, {stream: true});
      const lines = buffer.split("\\n");
      buffer = lines.pop() || "";

      let inEvent = false;
      let evType = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) {
          evType = line.slice(7).trim();
          inEvent = true;
        } else if (line.startsWith("data: ") && inEvent) {
          const data = line.slice(6).trim();
          inEvent = false;

          if (evType === "result" || evType === "thought") {
            full += data;
            contentDiv.textContent = full;
          } else if (evType === "status") {
            contentDiv.textContent = data;
          } else if (evType === "done") {
            contentDiv.textContent = full;
          }
        }
      }
    }
    chat.scrollTop = chat.scrollHeight;
  } catch(e) {
    contentDiv.textContent = "⚠️ 网络错误: " + e.message;
  }
  sendBtn.disabled = false;
  input.focus();
}"""

content = content[:idx] + new_ask + content[end_idx:]
with open(sys.argv[1], "w") as f:
    f.write(content)

print("✅ /ai page ask() replaced with streaming")
