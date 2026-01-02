export const MOCK_DOCUMENTS = [
  {
    id: '1',
    type: 'law',
    number: '7499',
    date: '12.03.2024',
    title: 'Ceza Muhakemesi Kanunu ile Bazı Kanunlarda Değişiklik Yapılmasına Dair Kanun',
    summary: 'Bu Kanun ile Ceza Muhakemesi Kanununda yapılan değişiklikler kapsamında, koruma tedbirleri nedeniyle tazminat istemlerinde süreler yeniden düzenlenmiş, hükmün açıklanmasının geri bırakılması (HAGB) kararına karşı istinaf yolu açılmıştır.',
    content: `# Ceza Muhakemesi Kanunu ile Bazı Kanunlarda Değişiklik Yapılmasına Dair Kanun

**Kanun No.** 7499  
**Kabul Tarihi:** 02.03.2024

**MADDE 1-** 4/12/2004 tarihli ve 5271 sayılı Ceza Muhakemesi Kanununun 141 inci maddesinin birinci fıkrasının (k) bendinde yer alan "Yakalama veya tutuklama" ibaresi "Yakalama, tutuklama veya adli kontrol" şeklinde değiştirilmiştir.

**MADDE 2-** 5271 sayılı Kanunun 142 nci maddesinin ikinci fıkrasına "karar" ibaresinden sonra gelmek üzere "veya hükümlerin" ibaresi eklenmiş ve dokuzuncu fıkrası aşağıdaki şekilde değiştirilmiştir.
"(9) Tazminat davaları; Yargıtay, Danıştay ve Sayıştay Başkan ve üyeleri, hakimler ve savcılar ile bu sınıftan sayılanlar hakkında kovuşturma yapılmasına yer olmadığına..."
    `
  },
  {
    id: '2',
    type: 'cb_karar',
    number: '158',
    date: '10.03.2024',
    title: 'Bazı Kurum ve Kuruluşlara Kadro İhdas Edilmesine İlişkin Cumhurbaşkanlığı Kararnamesi',
    summary: 'Çeşitli kamu kurum ve kuruluşlarının teşkilat yapılarında düzenlemeler yapılarak yeni kadrolar ihdas edilmiştir. Bu kapsamda Adalet Bakanlığı ve İçişleri Bakanlığı bünyesinde yeni uzmanlık kadroları oluşturulmuştur.',
    content: '...'
  },
  {
    id: '3',
    type: 'cb_yonetmelik',
    number: '32485',
    date: '08.03.2024',
    title: 'Yapay Zeka Sistemlerinin Güvenli Kullanımına Dair Yönetmelik Taslağı',
    summary: 'Kamu kurumlarında ve kritik altyapılarda kullanılacak yapay zeka sistemlerinin risk sınıflandırması, güvenlik standartları ve denetim mekanizmalarını belirleyen yeni yönetmelik.',
    content: '...'
  },
  {
    id: '4',
    type: 'law',
    number: '7498',
    date: '01.03.2024',
    title: 'Afet Riski Altındaki Alanların Dönüştürülmesi Hakkında Kanun Değişikliği',
    summary: 'Kentsel dönüşüm süreçlerini hızlandırmak amacıyla mülkiyet hakları, tespit ve yıkım süreçlerine ilişkin yeni düzenlemeler getirilmiştir.',
    content: '...'
  }
];

// Mock Data for Charts
export const MOCK_STATS = [
  { name: 'Jan', kanun: 4, khk: 1, cb_kararname: 2, cb_yonetmelik: 3, cb_karar: 2, cb_genelge: 1 },
  { name: 'Feb', kanun: 3, khk: 0, cb_kararname: 1, cb_yonetmelik: 4, cb_karar: 5, cb_genelge: 2 },
  { name: 'Mar', kanun: 7, khk: 2, cb_kararname: 3, cb_yonetmelik: 5, cb_karar: 3, cb_genelge: 4 },
  { name: 'Apr', kanun: 2, khk: 1, cb_kararname: 1, cb_yonetmelik: 2, cb_karar: 4, cb_genelge: 1 },
  { name: 'May', kanun: 5, khk: 0, cb_kararname: 4, cb_yonetmelik: 3, cb_karar: 6, cb_genelge: 3 },
  { name: 'Jun', kanun: 6, khk: 1, cb_kararname: 2, cb_yonetmelik: 4, cb_karar: 3, cb_genelge: 2 },
  { name: 'Jul', kanun: 3, khk: 2, cb_kararname: 1, cb_yonetmelik: 5, cb_karar: 5, cb_genelge: 4 },
  { name: 'Aug', kanun: 4, khk: 0, cb_kararname: 3, cb_yonetmelik: 2, cb_karar: 2, cb_genelge: 1 },
  { name: 'Sep', kanun: 8, khk: 3, cb_kararname: 5, cb_yonetmelik: 6, cb_karar: 6, cb_genelge: 5 },
  { name: 'Oct', kanun: 5, khk: 1, cb_kararname: 2, cb_yonetmelik: 4, cb_karar: 4, cb_genelge: 2 },
  { name: 'Nov', kanun: 6, khk: 0, cb_kararname: 1, cb_yonetmelik: 3, cb_karar: 3, cb_genelge: 1 },
  { name: 'Dec', kanun: 4, khk: 2, cb_kararname: 3, cb_yonetmelik: 4, cb_karar: 5, cb_genelge: 3 },
];

export const MOCK_STATS_DAILY = Array.from({ length: 30 }, (_, i) => ({
  name: `${i + 1}`,
  kanun: Math.floor(Math.random() * 3),
  khk: Math.floor(Math.random() * 2),
  cb_kararname: Math.floor(Math.random() * 3),
  cb_yonetmelik: Math.floor(Math.random() * 4),
  cb_karar: Math.floor(Math.random() * 3),
  cb_genelge: Math.floor(Math.random() * 2),
}));

export const MOCK_STATS_YEARLY = [
  { name: '2019', kanun: 45, khk: 12, cb_kararname: 20, cb_yonetmelik: 50, cb_karar: 23, cb_genelge: 15 },
  { name: '2020', kanun: 52, khk: 15, cb_kararname: 25, cb_yonetmelik: 60, cb_karar: 34, cb_genelge: 20 },
  { name: '2021', kanun: 48, khk: 10, cb_kararname: 22, cb_yonetmelik: 55, cb_karar: 29, cb_genelge: 18 },
  { name: '2022', kanun: 61, khk: 18, cb_kararname: 30, cb_yonetmelik: 70, cb_karar: 42, cb_genelge: 25 },
  { name: '2023', kanun: 55, khk: 14, cb_kararname: 28, cb_yonetmelik: 65, cb_karar: 38, cb_genelge: 22 },
  { name: '2024', kanun: 18, khk: 5, cb_kararname: 10, cb_yonetmelik: 20, cb_karar: 12, cb_genelge: 8 },
];

export type DocType = 'law' | 'khk' | 'cb_kararname' | 'cb_yonetmelik' | 'cb_karar' | 'cb_genelge';

export const DOC_TYPE_LABELS = {
  law: { tr: 'Kanun', en: 'Law' },
  khk: { tr: 'KHK', en: 'Decree Law' },
  cb_kararname: { tr: 'CB Kararnamesi', en: 'Pres. Decree' },
  cb_yonetmelik: { tr: 'CB Yönetmeliği', en: 'Pres. Regulation' },
  cb_karar: { tr: 'CB Kararı', en: 'Pres. Decision' },
  cb_genelge: { tr: 'CB Genelgesi', en: 'Pres. Circular' },
};