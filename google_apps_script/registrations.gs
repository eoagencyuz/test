/**
 * Telegram botdan kelgan ro'yxatdan o'tganlarni Google Sheets'ga yozadi.
 *
 * O'rnatish: README.md dagi "Google Sheets" bo'limiga qarang.
 * Maxfiy kalit "Script properties" ichida SECRET nomi bilan saqlanadi
 * (botdagi SHEETS_SECRET bilan bir xil bo'lishi kerak).
 * Skript jadvaldan tashqarida (script.google.com orqali) yaratilgan bo'lsa,
 * "Script properties" ga SPREADSHEET_ID ham qo'shing (jadval havolasidagi /d/ dan keyingi qism).
 */
const SHEET_NAME = "Ro'yxatdan o'tganlar";
const HEADERS = [
  "Telegram ID", "Username", "F.I.Sh.", "Telefon", "Pasport", "HEMIS ID", "Ro'yxatdan o'tgan vaqt",
];

function jsonOutput(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  let body;
  try {
    body = JSON.parse(e.postData.contents);
  } catch (err) {
    return jsonOutput({ ok: false, error: "bad_request" });
  }

  const secret = PropertiesService.getScriptProperties().getProperty("SECRET");
  if (!secret || body.secret !== secret) {
    return jsonOutput({ ok: false, error: "unauthorized" });
  }

  // Rassilka uchun: bot ro'yxatdan o'tganlar ro'yxatini so'raydi
  if (body.action === "list") {
    return jsonOutput({ ok: true, rows: listRows() });
  }

  const r = body.record || {};
  const values = [
    String(r.telegram_id || ""),
    r.username ? "@" + r.username : "",
    r.full_name || "",
    r.phone || "",
    r.passport || "",
    r.hemis_id || "",
    r.registered_at || "",
  ];
  if (!values[0] || !values[5]) {
    return jsonOutput({ ok: false, error: "bad_record" });
  }

  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const spreadsheetId = PropertiesService.getScriptProperties().getProperty("SPREADSHEET_ID");
    const ss = spreadsheetId ? SpreadsheetApp.openById(spreadsheetId) : SpreadsheetApp.getActiveSpreadsheet();
    if (!ss) {
      return jsonOutput({ ok: false, error: "no_spreadsheet" });
    }
    const sheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(HEADERS);
      sheet.setFrozenRows(1);
      sheet.getRange(1, 1, 1, HEADERS.length).setFontWeight("bold");
    }

    // Shu Telegram ID bilan qator bo'lsa yangilanadi, bo'lmasa yangi qator qo'shiladi
    const lastRow = sheet.getLastRow();
    let row = lastRow + 1;
    if (lastRow > 1) {
      const ids = sheet.getRange(2, 1, lastRow - 1, 1).getDisplayValues();
      for (let i = 0; i < ids.length; i++) {
        if (ids[i][0] === values[0]) {
          row = i + 2;
          break;
        }
      }
    }

    const range = sheet.getRange(row, 1, 1, values.length);
    range.setNumberFormat("@"); // telefon, pasport va HEMIS ID matn sifatida saqlansin
    range.setValues([values]);
    return jsonOutput({ ok: true, row: row });
  } finally {
    lock.releaseLock();
  }
}

/**
 * Sinov: Apps Script'da shu funksiyani tanlab "Выполнить / Run" bosing.
 * Jadvalda "SINOV QATORI" paydo bo'lsa, skript to'g'ri ishlayapti (keyin qatorni o'chiring).
 */
function testYozish() {
  const secret = PropertiesService.getScriptProperties().getProperty("SECRET");
  const e = { postData: { contents: JSON.stringify({
    secret: secret,
    record: { telegram_id: "TEST", full_name: "SINOV QATORI", hemis_id: "TEST" },
  }) } };
  Logger.log(doPost(e).getContent());
}

/**
 * Ro'yxatdan o'tganlar (rassilka uchun): sarlavhadagi "Telegram ID", "F.I.Sh.", "HEMIS ID" ustunlari bo'yicha.
 */
function listRows() {
  const spreadsheetId = PropertiesService.getScriptProperties().getProperty("SPREADSHEET_ID");
  const ss = spreadsheetId ? SpreadsheetApp.openById(spreadsheetId) : SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss && ss.getSheetByName(SHEET_NAME);
  if (!sheet || sheet.getLastRow() < 2) {
    return [];
  }
  const values = sheet.getDataRange().getDisplayValues();
  const header = values[0];
  const idCol = header.indexOf("Telegram ID");
  const nameCol = header.indexOf("F.I.Sh.");
  const hemisCol = header.indexOf("HEMIS ID");
  if (idCol < 0) {
    return [];
  }
  return values.slice(1).map(function (row) {
    return {
      telegram_id: row[idCol],
      full_name: nameCol >= 0 ? row[nameCol] : "",
      hemis_id: hemisCol >= 0 ? row[hemisCol] : "",
    };
  });
}
