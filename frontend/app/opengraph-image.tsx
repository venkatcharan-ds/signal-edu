import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "SIGNAL — We surface the talent that credentials hide";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          background: "#080808",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          justifyContent: "flex-end",
          padding: "72px 80px",
          fontFamily: "sans-serif",
        }}
      >
        {/* Accent glow */}
        <div
          style={{
            position: "absolute",
            top: 0,
            right: 0,
            width: 600,
            height: 600,
            background:
              "radial-gradient(circle at 100% 0%, rgba(99,102,241,0.18) 0%, transparent 60%)",
          }}
        />

        {/* Score preview boxes */}
        <div
          style={{
            position: "absolute",
            top: 72,
            right: 80,
            display: "flex",
            gap: 16,
          }}
        >
          {[
            { label: "TE", value: "7.4" },
            { label: "PC", value: "6.8" },
            { label: "CQ", value: "7.1" },
          ].map(({ label, value }) => (
            <div
              key={label}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.10)",
                borderRadius: 12,
                padding: "20px 28px",
                gap: 6,
              }}
            >
              <span style={{ color: "#6366f1", fontSize: 13, fontWeight: 600, letterSpacing: 2 }}>
                {label}
              </span>
              <span style={{ color: "#ffffff", fontSize: 36, fontWeight: 700 }}>
                {value}
              </span>
            </div>
          ))}
        </div>

        {/* Wordmark */}
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 28 }}>
          <span
            style={{
              fontSize: 22,
              fontWeight: 700,
              color: "#ffffff",
              letterSpacing: 6,
              textTransform: "uppercase",
            }}
          >
            SIGNAL
          </span>
          <div
            style={{
              width: 1,
              height: 22,
              background: "rgba(255,255,255,0.2)",
            }}
          />
          <span style={{ fontSize: 14, color: "rgba(255,255,255,0.4)", letterSpacing: 1 }}>
            EDU
          </span>
        </div>

        {/* Headline */}
        <h1
          style={{
            fontSize: 56,
            fontWeight: 700,
            color: "#ffffff",
            lineHeight: 1.1,
            margin: 0,
            marginBottom: 20,
            maxWidth: 700,
          }}
        >
          We surface the talent that credentials hide.
        </h1>

        {/* Sub */}
        <p
          style={{
            fontSize: 22,
            color: "rgba(255,255,255,0.45)",
            margin: 0,
            maxWidth: 580,
            lineHeight: 1.4,
          }}
        >
          Evidence-based capability profiles built from real GitHub work — not resumes.
        </p>
      </div>
    ),
    { ...size }
  );
}
