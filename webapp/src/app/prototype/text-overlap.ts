function bigrams(s: string): Map<string, number> {
  const lower = s.toLowerCase();
  const counts = new Map<string, number>();
  for (let i = 0; i < lower.length - 1; i++) {
    const pair = lower.slice(i, i + 2);
    counts.set(pair, (counts.get(pair) ?? 0) + 1);
  }
  return counts;
}

export function overlapCoefficient(a: string, b: string): number {
  if (a.length < 4 || b.length < 4) return 0;
  const ba = bigrams(a);
  const bb = bigrams(b);
  let intersection = 0;
  for (const [pair, count] of ba) {
    intersection += Math.min(count, bb.get(pair) ?? 0);
  }
  const sizeA = a.length - 1;
  const sizeB = b.length - 1;
  return intersection / Math.min(sizeA, sizeB);
}

export function maxOverlap(text: string, targets: string[]): number {
  if (targets.length === 0) return 0;
  let max = 0;
  for (const t of targets) {
    const score = overlapCoefficient(text, t);
    if (score > max) max = score;
  }
  return max;
}
