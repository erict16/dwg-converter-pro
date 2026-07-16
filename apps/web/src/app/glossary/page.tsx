import glossary from "@/data/semantic-glossary.json";

export default function GlossaryPage() {
  const entries = glossary.entries.slice(0, 50);

  return (
    <div className="hero">
      <h1>Semantic glossary</h1>
      <p>
        Technical terms loaded from{" "}
        <code>data/semantic-glossary.json</code> ({glossary.count} pairs). First
        50 rows shown here for the UI shell.
      </p>

      <div className="grid-2">
        <div className="stat">
          <div className="label">Entries</div>
          <div className="value">{glossary.count}</div>
        </div>
        <div className="stat">
          <div className="label">Source</div>
          <div className="value" style={{ fontSize: "1rem" }}>
            {glossary.source}
          </div>
        </div>
        <div className="stat">
          <div className="label">Priority</div>
          <div className="value" style={{ fontSize: "1rem" }}>
            Longest match first
          </div>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th style={{ width: "38%" }}>中文术语</th>
              <th style={{ width: "42%" }}>English</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((row) => (
              <tr key={`${row.zh}-${row.en}`}>
                <td>{row.zh}</td>
                <td>{row.en}</td>
                <td>{row.note || <span className="badge">—</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
