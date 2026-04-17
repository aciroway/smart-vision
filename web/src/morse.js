export const MORSE = {
  // EN
  A: ".-",
  B: "-...",
  C: "-.-.",
  D: "-..",
  E: ".",
  F: "..-.",
  G: "--.",
  H: "....",
  I: "..",
  J: ".---",
  K: "-.-",
  L: ".-..",
  M: "--",
  N: "-.",
  O: "---",
  P: ".--.",
  Q: "--.-",
  R: ".-.",
  S: "...",
  T: "-",
  U: "..-",
  V: "...-",
  W: ".--",
  X: "-..-",
  Y: "-.--",
  Z: "--..",
  // digits
  0: "-----",
  1: ".----",
  2: "..---",
  3: "...--",
  4: "....-",
  5: ".....",
  6: "-....",
  7: "--...",
  8: "---..",
  9: "----.",
  // RU
  "А": ".-",
  "Б": "-...",
  "В": ".--",
  "Г": "--.",
  "Д": "-..",
  "Е": ".",
  "Ж": "...-",
  "З": "--..",
  "И": "..",
  "Й": ".---",
  "К": "-.-",
  "Л": ".-..",
  "М": "--",
  "Н": "-.",
  "О": "---",
  "П": ".--.",
  "Р": ".-.",
  "С": "...",
  "Т": "-",
  "У": "..-",
  "Ф": "..-.",
  "Х": "....",
  "Ц": "-.-.",
  "Ч": "---.",
  "Ш": "----",
  "Щ": "--.-",
  "Ъ": "--.--",
  "Ы": "-.--",
  "Ь": "-..-",
  "Э": "..-..",
  "Ю": "..--",
  "Я": ".-.-",
  // punctuation
  ".": ".-.-.-",
  ",": "--..--",
  "?": "..--..",
  "!": "-.-.--",
  ":": "---...",
  ";": "-.-.-.",
  "(": "-.--.",
  ")": "-.--.-",
  "-": "-....-",
  "/": "-..-.",
  "\"": ".-..-.",
  "'": ".----.",
  "@": ".--.-.",
  "=": "-...-"
};

export function normalizeText(text) {
  return String(text || "")
    .toUpperCase()
    .replaceAll("Ё", "Е")
    .trim()
    .replace(/\s+/g, " ");
}

export function textToMorse(text) {
  const t = normalizeText(text);
  if (!t) return "";
  const words = [];
  for (const word of t.split(" ")) {
    const letters = [];
    for (const ch of word) {
      const code = MORSE[ch];
      if (code) letters.push(code);
    }
    if (letters.length) words.push(letters.join(" "));
  }
  return words.join(" / ");
}

export const TIMINGS = {
  dot: 150,
  dash: 450,
  gap: 100,
  letterGap: 300,
  wordGap: 600
};

export function morseToPattern(morse) {
  const s = String(morse || "").trim();
  if (!s) return [];

  const { dot, dash, gap, letterGap, wordGap } = TIMINGS;
  const pattern = [];

  const tokens = s.split("");
  for (let i = 0; i < tokens.length; i++) {
    const ch = tokens[i];
    if (ch === "." || ch === "-") {
      pattern.push(ch === "." ? dot : dash);
      const next = tokens[i + 1];
      if (next === "." || next === "-") pattern.push(gap);
    } else if (ch === "/") {
      pattern.push(wordGap);
    } else if (ch === " ") {
      const prev = tokens[i - 1];
      const next = tokens[i + 1];
      if ((prev === "." || prev === "-") && next && next !== "/" && next !== " ") {
        pattern.push(letterGap);
      }
    }
  }
  return pattern;
}

