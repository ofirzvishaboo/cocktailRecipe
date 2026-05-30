// ─────────────────────────────────────────────
// The Cocktail Factory – full bar menu data
// Source: physical menu photos (May 2026)
// ─────────────────────────────────────────────

export const WINES = {
  white: [
    { name: 'Janela Branca', nameHe: 'ג׳נלה ברנקה', origin: 'Portugal', priceIls: 38 },
    { name: 'Yarden Har Hermon', nameHe: 'ירדן הר הרמון', origin: 'Israel', priceIls: 41 },
    { name: 'Luis Eschenhauer – S.Blanc', nameHe: 'לואיס אשנהאואר – סוביניון בלאן', origin: 'France', priceIls: 43 },
    { name: 'Kastel La Vie', nameHe: 'קסטל לה-וי', origin: 'Israel', priceIls: 45 },
    { name: 'Chablis', nameHe: 'שבליס', origin: 'France', priceIls: 61 },
    { name: 'Hans Baer – Gorz', nameHe: 'האנס בר – גורץ', origin: 'Germany', priceIls: 47 },
  ],
  rose: [
    { name: 'Janela Branca Rosé', nameHe: 'ג׳נלה ברנקה רוזה', origin: 'Portugal', priceIls: 40 },
    { name: 'Miraval', nameHe: 'מירוול', origin: 'France', priceIls: 65 },
  ],
  red: [
    { name: 'Piccini Memoro', nameHe: 'פיצ׳יני ממורו', origin: 'Italy', priceIls: 40 },
    { name: 'Janela Branca Red', nameHe: 'ג׳נלה ברנקה אדום', origin: 'Portugal', priceIls: 41 },
    { name: 'Kastel La Vie', nameHe: 'קסטל לה-וי', origin: 'Israel', priceIls: 45 },
  ],
}

export const BEERS = {
  tap: [
    { name: 'Hobgoblin IPA', nameHe: 'הובגובלין IPA', note: 'English IPA', priceIls: 32 },
    { name: 'Tucher Lager', nameHe: 'טוכר לאגר', note: 'German lager', priceIls: 29 },
    { name: 'Tucher Weiss', nameHe: 'טוכר ווייס', note: 'Wheat beer', priceIls: 29 },
  ],
  bottle: [
    { name: 'Peroni', nameHe: 'פרוני', note: 'Italian lager', priceIls: 29 },
    { name: 'Flora Cactus & Lime', nameHe: 'פלורה קקטוס וליים', note: 'Refreshing beer', priceIls: 31 },
    { name: 'Kozel Dark Lager', nameHe: 'קוזל דארק', note: 'Czech dark lager', priceIls: 31 },
    { name: 'Guinness', nameHe: 'גינס', note: 'Irish stout', priceIls: 32 },
  ],
  can: [
    { name: 'Brewdog Wingman', nameHe: 'ברודוג ווינגמן', note: 'Session IPA', priceIls: 31 },
    { name: 'Brewdog Fruit Burst', nameHe: 'ברודוג פרוט ברסט', note: 'Fruity sour', priceIls: 31 },
    { name: 'Brewdog X-Mass Edition', nameHe: 'ברודוג מהדורת חג', note: 'Spiced beer', priceIls: 31 },
    { name: 'Brewdog Hazy Jane', nameHe: 'ברודוג הייזי ג׳ין', note: 'Hazy IPA', priceIls: 31 },
    { name: 'Shoshana', nameHe: 'שושנה', note: 'Israeli craft beer', priceIls: 32 },
  ],
  sparkling: [
    { name: 'Gancia Prosecco', nameHe: 'גנציה פרוסקו', origin: 'Italy', priceIls: 43 },
    { name: 'Alfabeto – Vento', nameHe: 'אלפבטו – וונטו', origin: 'Italy', priceIls: 47 },
  ],
}

export const SPIRITS = {
  vodka: [
    { name: 'Mont Blanc', nameHe: 'מון בלאן', priceIls: 50 },
    { name: 'Stoli Elite', nameHe: 'סטולי אליט', priceIls: 55 },
    { name: 'Żubrówka – Bison Grass', nameHe: 'זוברובקה – עשב הביזון', priceIls: 48 },
    { name: 'Thinkers Vodka', nameHe: 'ת׳ינקרס וודקה', priceIls: 54 },
  ],
  gin: [
    { name: "Greenall's", nameHe: 'גרינלס', priceIls: 46 },
    { name: 'Gunpowder Gin', nameHe: 'גאנפאודר ג׳ין', priceIls: 50 },
    { name: 'Milk & Honey Levantine', nameHe: 'מילק & האני לוואנטין', priceIls: 50 },
    { name: 'Milk & Honey Orange', nameHe: 'מילק & האני תפוז', priceIls: 50 },
    { name: 'Petter Gin', nameHe: 'פטר ג׳ין', priceIls: 50 },
    { name: 'Gin Salers', nameHe: 'ג׳ין סאלרס', priceIls: 50 },
    { name: 'Antidote', nameHe: 'אנטידוט', priceIls: 50 },
    { name: 'Tanqueray Sevilla', nameHe: 'טנקריי סביליה', priceIls: 50 },
    { name: 'Barrister Blue', nameHe: 'בריסטר בלו', priceIls: 50 },
    { name: 'Thinkers Gin', nameHe: 'ת׳ינקרס ג׳ין', priceIls: 54 },
  ],
  rum: [
    { name: 'St. James Imperial', nameHe: 'סיינט ג׳יימס אימפריאל', priceIls: 50 },
    { name: 'Kraken', nameHe: 'קראקן', priceIls: 50 },
    { name: 'Havana Club', nameHe: 'הוואנה קלאב', priceIls: 48 },
    { name: 'Compagnie des Indes', nameHe: 'קומפני דה אינד', priceIls: 61 },
  ],
  agave: [
    { name: 'Lunazul', nameHe: 'לונאזול', priceIls: 50 },
    { name: 'Don Ramon Platinum', nameHe: 'דון רמון פלטינום', priceIls: 54 },
    { name: 'Don Julio 1792', nameHe: 'דון חוליו 1792', priceIls: 71 },
    { name: 'Volcan Tequila', nameHe: 'וולקאן טקילה', priceIls: 65 },
    { name: '1800 Coconut', nameHe: '1800 קוקוס', priceIls: 57 },
    { name: 'San Cosme Mezcal', nameHe: 'סן קוסמה מזקל', priceIls: 61 },
    { name: '1800 Cristalino Tequila', nameHe: '1800 קריסטאלינו טקילה', priceIls: 63 },
    { name: 'Rooster Blanco Tequila', nameHe: 'רוסטר בלאנקו טקילה', priceIls: 56 },
  ],
  whiskey: [
    { name: 'GlenCadam', nameHe: 'גלנקדם', priceIls: 50 },
    { name: 'Loch Lomond Blended', nameHe: 'לוך לומונד בלנדד', priceIls: 46 },
    { name: 'Loch Lomond 10', nameHe: 'לוך לומונד 10', priceIls: 61 },
    { name: 'Glen Scotia 10', nameHe: 'גלן סקוטיה 10', priceIls: 65 },
    { name: 'Tomintoul 14', nameHe: 'טומינטול 14', priceIls: 71 },
    { name: 'The Glenlivet 15', nameHe: 'הגלנליוות 15', priceIls: 82 },
    { name: 'Ole Smoky Peanut Butter', nameHe: 'אולד סמוקי חמאת בוטנים', priceIls: 50 },
    { name: 'M&H Classic', nameHe: 'מילק & האני קלאסיק', priceIls: 50 },
    { name: 'M&H Elements Sherry', nameHe: 'מילק & האני אלמנטס שרי', priceIls: 57 },
    { name: 'House Blend Whiskey', nameHe: 'ויסקי הבית', priceIls: 46 },
  ],
  cognac: [
    { name: 'Cognac Godet VS', nameHe: 'קוניאק גודה VS', priceIls: 40 },
    { name: 'Hine VSOP', nameHe: 'היין VSOP', priceIls: 50 },
    { name: 'Davidoff XO', nameHe: 'דוידוף XO', priceIls: 82 },
    { name: 'Cognac Godet', nameHe: 'קוניאק גודה', priceIls: 55 },
  ],
  aperitif: [
    { name: 'Pampelle', nameHe: 'פמפל', priceIls: 46 },
    { name: 'Lillet Blanc', nameHe: 'לילה בלאן', priceIls: 44 },
    { name: 'Lillet Rosé', nameHe: 'לילה רוזה', priceIls: 44 },
    { name: 'Venti', nameHe: 'ונטי', priceIls: 44 },
    { name: 'Suze', nameHe: 'סוז', priceIls: 46 },
    { name: 'Petter Vermouth', nameHe: 'פטר וורמוט', priceIls: 46 },
    { name: 'Dolin Vermouth', nameHe: 'דולן וורמוט', priceIls: 46 },
  ],
  liqueur: [
    { name: 'Luxardo', nameHe: 'לוקסארדו', note: 'Maraschino / Green Apple / Del Santo / Brandy Apricot', priceIls: 42 },
    { name: 'Moradova', nameHe: 'מורדובה', note: 'Etrog / Dates', priceIls: 42 },
    { name: 'Le Birlou', nameHe: 'לה בירלו', priceIls: 42 },
    { name: 'Jägermeister', nameHe: 'יגרמייסטר', priceIls: 46 },
  ],
  homemadeLiqueur: [
    { name: 'Dionisius LimeCello', nameHe: 'דיוניסוס לימצ׳לו', priceIls: 42 },
    { name: 'Dionisius Coffee', nameHe: 'דיוניסוס קפה', priceIls: 42 },
    { name: 'Nastia Oblipheha', nameHe: 'נסטיה אובליפה', priceIls: 42 },
    { name: 'Nastia Berry & Basil', nameHe: 'נסטיה פירות יער ובזיליקום', priceIls: 42 },
    { name: 'Nastia Rum Liqueur', nameHe: 'נסטיה ליקר רום', note: 'Pears, Oolong Tea, Cinnamon, Vanilla', priceIls: 42 },
  ],
  anise: [
    { name: 'Yuka Arak', nameHe: 'יוקה ערק', priceIls: 44 },
    { name: 'Ouzo', nameHe: 'אוזו', priceIls: 44 },
    { name: 'Absinthe (Katrin Distillery)', nameHe: 'אבסינת׳ (קטרין דיסטילרי)', priceIls: 44 },
  ],
  addOns: [
    { name: 'Tonic', nameHe: 'טוניק', priceIls: 13 },
    { name: 'Ginger Ale', nameHe: 'ג׳ינג׳ר אייל', priceIls: 13 },
    { name: 'Ginger Beer', nameHe: 'ג׳ינג׳ר בירה', priceIls: 13 },
    { name: 'Cranberry', nameHe: 'חמוציות', priceIls: 13 },
    { name: 'Apple Lime', nameHe: 'תפוח ליים', priceIls: 13 },
    { name: 'Borgomi Soda', nameHe: 'בורגומי סודה', priceIls: 13 },
  ],
}
