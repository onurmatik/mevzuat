export type DocType = 'kanun' | 'khk' | 'cb-kararname' | 'cb-yonetmelik' | 'cb-karar' | 'cb-genelge';

export const DOC_TYPE_LABELS = {
  kanun: { tr: 'Kanun', en: 'Law' },
  khk: { tr: 'KHK', en: 'Decree Law' },
  'cb-kararname': { tr: 'CB Kararnamesi', en: 'Pres. Decree' },
  'cb-yonetmelik': { tr: 'CB Yönetmeliği', en: 'Pres. Regulation' },
  'cb-karar': { tr: 'CB Kararı', en: 'Pres. Decision' },
  'cb-genelge': { tr: 'CB Genelgesi', en: 'Pres. Circular' },
};
