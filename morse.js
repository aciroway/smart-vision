export const MORSE = {
  // English
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
  // Digits
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
  // Russian (common ITU / RU standard)
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
  // Punctuation (basic)
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
  const t = String(text || "")
    .toUpperCase()
    .replaceAll("Ё", "Е")
    .trim()
    .replace(/\s+/g, " ");
  return t;
}

// letters separated by spaces, words separated by " / "
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

