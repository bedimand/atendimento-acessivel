import { useCallback, useMemo } from "react";

export function useSpeechSynthesis() {
  const synth = useMemo(() => window.speechSynthesis, []);
  const supported = typeof synth !== "undefined";

  const speak = useCallback(
    (text: string) => {
      if (!supported) return;
      synth.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1;
      synth.speak(utterance);
    },
    [supported, synth],
  );

  const cancel = useCallback(() => {
    if (!supported) return;
    synth.cancel();
  }, [supported, synth]);

  return { supported, speak, cancel };
}
