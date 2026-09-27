// Bridge between LayaClient (Python) and Laya (Node.js/ONNX Runtime).
//
// Reads one JSON payload from stdin: {"state": <any>, "questions": [{"id", "statement"}, ...]}
// Asks all questions as "noul" primitives in a single Laya systemOne() pass and writes one
// JSON response to stdout: {"answers": [{"id", "probability"}, ...]}
import { Laya } from "@receptron/laya";

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => (data += chunk));
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
}

async function main() {
  const { state, questions } = JSON.parse(await readStdin());

  const questionMap = {};
  for (const q of questions) {
    questionMap[q.id] = { type: "noul", instructions: q.statement };
  }

  const laya = await Laya.load();
  try {
    const result = await laya.systemOne(state, questionMap);
    const answers = questions.map((q) => ({
      id: q.id,
      probability: result.answers[q.id].noul,
    }));
    process.stdout.write(JSON.stringify({ answers }));
  } finally {
    await laya.close();
  }
}

main().catch((err) => {
  process.stderr.write(err && err.stack ? err.stack : String(err));
  process.exit(1);
});
