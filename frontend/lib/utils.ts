import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

const RELATIVE_TIME_UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 60 * 60 * 24 * 365],
  ["month", 60 * 60 * 24 * 30],
  ["week", 60 * 60 * 24 * 7],
  ["day", 60 * 60 * 24],
  ["hour", 60 * 60],
  ["minute", 60],
];

const relativeTimeFormatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

/** e.g. "3 hours ago", "just now" — used for session timestamps. */
export function formatRelativeTime(isoDate: string): string {
  const seconds = (new Date(isoDate).getTime() - Date.now()) / 1000;

  for (const [unit, unitSeconds] of RELATIVE_TIME_UNITS) {
    if (Math.abs(seconds) >= unitSeconds) {
      return relativeTimeFormatter.format(Math.round(seconds / unitSeconds), unit);
    }
  }
  return "just now";
}
