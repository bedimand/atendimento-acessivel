import { useEffect, useRef } from "react";

declare global {
  interface Window {
    VLibras?: {
      Widget: new (url: string) => void;
    };
  }
}

export function VLibrasWidget() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const accessButtonRef = useRef<HTMLDivElement | null>(null);
  const pluginWrapperRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const existing = document.getElementById("vlibras-loader");
    if (!existing) {
      const script = document.createElement("script");
      script.id = "vlibras-loader";
      script.src = "https://vlibras.gov.br/app/vlibras-plugin.js";
      script.async = true;
      script.onload = () => {
        if (window.VLibras) {
          new window.VLibras.Widget("https://vlibras.gov.br/app");
        }
      };
      document.body.appendChild(script);
    }

    containerRef.current?.setAttribute("vw", "enabled");
    accessButtonRef.current?.setAttribute("vw-access-button", "true");
    pluginWrapperRef.current?.setAttribute("vw-plugin-wrapper", "true");
  }, []);

  return (
    <div className="vlibras-widget" aria-label="Plugin VLibras">
      <div ref={containerRef} className="enabled">
        <div ref={accessButtonRef} className="active"></div>
        <div ref={pluginWrapperRef}>
          <div className="vw-plugin-top-wrapper"></div>
        </div>
      </div>
    </div>
  );
}
