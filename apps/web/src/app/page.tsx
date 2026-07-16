import { ConverterShell } from "@/components/ConverterShell";

export default function HomePage() {
  return (
    <div className="hero">
      <h1>Chinese drawings → English</h1>
      <p>
        Drop one or many DWG/DXF files. We translate text in place (including
        leader notes) using the technical glossary first, then free
        machine translation for leftovers. Geometry stays put.
      </p>
      <div className="grid-3">
        <div className="stat">
          <div className="label">Batch queue</div>
          <div className="value">Multi-file</div>
        </div>
        <div className="stat">
          <div className="label">Terms</div>
          <div className="value">393 glossary</div>
        </div>
        <div className="stat">
          <div className="label">Theme</div>
          <div className="value">Dark / Light</div>
        </div>
      </div>
      <ConverterShell />
    </div>
  );
}
