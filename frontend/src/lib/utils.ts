import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Map backend slugs/names to frontend DocType keys
export function mapSlugToDocType(slug: string): string {
  if (!slug) return 'other';
  const s = slug.toLowerCase().trim();

  if (s.includes('kanun') && !s.includes('hükmünde')) return 'law';
  if (s.includes('khk') || s.includes('kanun-hukmunde') || s.includes('hükmünde')) return 'khk';
  if (s.includes('kararname') || s.includes('cumhurbaskanligi-kararnamesi')) return 'cb_kararname';
  if (s.includes('yonetmelik') || s.includes('yönetmelik')) return 'cb_yonetmelik';
  if (s.includes('genelge')) return 'cb_genelge';
  if (s.includes('karar') && s.includes('cumhurbaskanligi')) return 'cb_karar';
  if (s === 'cb-karar') return 'cb_karar'; // exact slug match if backend uses short names

  // Fallback: try to match known keys directly
  if (['law', 'khk', 'cb_kararname', 'cb_yonetmelik', 'cb_karar', 'cb_genelge'].includes(s.replace(/-/g, '_'))) {
    return s.replace(/-/g, '_');
  }

  return 'other'; // default
}