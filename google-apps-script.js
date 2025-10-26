/**
 * Google Apps Script для удалённого запуска парсера Ozon
 * Размещается в Google Sheets: Расширения -> Apps Script
 */

// ========== НАСТРОЙКИ (ИЗМЕНИТЕ НА СВОИ!) ==========

// URL вашего API сервера на Timeweb
const API_BASE_URL = 'http://your-server-ip:8000';

// API секретный ключ (тот же, что в .env на сервере)
const API_SECRET_KEY = 'your_api_secret_key_here';

// ====================================================


/**
 * Создание кастомного меню в Google Sheets
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('🤖 Ozon Parser')
    .addItem('▶️ Запустить парсинг', 'triggerParser')
    .addItem('📊 Проверить статус', 'checkParserStatus')
    .addItem('📋 Показать логи', 'showParserLogs')
    .addSeparator()
    .addItem('⚙️ Настройки API', 'showApiSettings')
    .addToUi();
}


/**
 * Запуск парсера через API
 */
function triggerParser() {
  const ui = SpreadsheetApp.getUi();
  
  // Подтверждение запуска
  const response = ui.alert(
    'Запуск парсера',
    'Запустить парсинг заказов Ozon?',
    ui.ButtonSet.YES_NO
  );
  
  if (response !== ui.Button.YES) {
    return;
  }
  
  try {
    // Отправка POST запроса
    const url = `${API_BASE_URL}/trigger`;
    const payload = {
      source: 'app_script',
      force: false
    };
    
    const options = {
      method: 'post',
      contentType: 'application/json',
      headers: {
        'Authorization': `Bearer ${API_SECRET_KEY}`
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    
    const result = UrlFetchApp.fetch(url, options);
    const statusCode = result.getResponseCode();
    const data = JSON.parse(result.getContentText());
    
    if (statusCode === 200 || statusCode === 202) {
      ui.alert(
        '✅ Успешно',
        `Парсер запущен!\n\nВремя запуска: ${data.started_at}\nСтатус: ${data.status}`,
        ui.ButtonSet.OK
      );
    } else if (statusCode === 409) {
      ui.alert(
        '⚠️ Внимание',
        'Парсер уже выполняется.\n\nДождитесь завершения текущей задачи.',
        ui.ButtonSet.OK
      );
    } else if (statusCode === 401) {
      ui.alert(
        '🔒 Ошибка авторизации',
        'Неверный API ключ!\n\nПроверьте настройки в скрипте.',
        ui.ButtonSet.OK
      );
    } else {
      throw new Error(`HTTP ${statusCode}: ${data.detail || result.getContentText()}`);
    }
    
  } catch (error) {
    ui.alert(
      '❌ Ошибка',
      `Не удалось запустить парсер:\n\n${error.message}`,
      ui.ButtonSet.OK
    );
    Logger.log('Error triggering parser: ' + error);
  }
}


/**
 * Проверка статуса парсера
 */
function checkParserStatus() {
  const ui = SpreadsheetApp.getUi();
  
  try {
    const url = `${API_BASE_URL}/status`;
    const options = {
      method: 'get',
      headers: {
        'Authorization': `Bearer ${API_SECRET_KEY}`
      },
      muteHttpExceptions: true
    };
    
    const result = UrlFetchApp.fetch(url, options);
    const statusCode = result.getResponseCode();
    
    if (statusCode !== 200) {
      throw new Error(`HTTP ${statusCode}: ${result.getContentText()}`);
    }
    
    const response = JSON.parse(result.getContentText());
    const status = response.data;
    
    // Формирование сообщения
    let message = '';
    
    if (status.is_running) {
      message = `🔄 ВЫПОЛНЯЕТСЯ\n\n`;
      message += `Запущен: ${formatDateTime(status.started_at)}\n`;
    } else {
      message = `⏸️ ОСТАНОВЛЕН\n\n`;
      
      if (status.last_run) {
        message += `Последний запуск: ${formatDateTime(status.last_run)}\n`;
        message += `Статус: ${status.last_status === 'success' ? '✅ Успешно' : '❌ Ошибка'}\n`;
        
        if (status.last_error) {
          message += `\nОшибка: ${status.last_error.substring(0, 200)}`;
        }
      } else {
        message += `Парсер ещё ни разу не запускался`;
      }
    }
    
    ui.alert('📊 Статус парсера', message, ui.ButtonSet.OK);
    
  } catch (error) {
    ui.alert(
      '❌ Ошибка',
      `Не удалось получить статус:\n\n${error.message}`,
      ui.ButtonSet.OK
    );
    Logger.log('Error checking status: ' + error);
  }
}


/**
 * Показать последние логи
 */
function showParserLogs() {
  const ui = SpreadsheetApp.getUi();
  
  try {
    const url = `${API_BASE_URL}/logs?lines=50`;
    const options = {
      method: 'get',
      headers: {
        'Authorization': `Bearer ${API_SECRET_KEY}`
      },
      muteHttpExceptions: true
    };
    
    const result = UrlFetchApp.fetch(url, options);
    const statusCode = result.getResponseCode();
    
    if (statusCode !== 200) {
      throw new Error(`HTTP ${statusCode}: ${result.getContentText()}`);
    }
    
    const response = JSON.parse(result.getContentText());
    const logs = response.logs || [];
    
    if (logs.length === 0) {
      ui.alert('📋 Логи', 'Логи не найдены', ui.ButtonSet.OK);
      return;
    }
    
    // Показываем последние 20 строк (для читаемости)
    const lastLogs = logs.slice(-20).join('\n');
    
    ui.alert(
      '📋 Последние логи',
      `Файл: ${response.log_file}\nСтрок: ${response.lines_count}\n\n${lastLogs.substring(0, 1000)}`,
      ui.ButtonSet.OK
    );
    
    // Полные логи в консоль
    Logger.log('Full logs:');
    logs.forEach(log => Logger.log(log));
    
  } catch (error) {
    ui.alert(
      '❌ Ошибка',
      `Не удалось получить логи:\n\n${error.message}`,
      ui.ButtonSet.OK
    );
    Logger.log('Error fetching logs: ' + error);
  }
}


/**
 * Показать настройки API
 */
function showApiSettings() {
  const ui = SpreadsheetApp.getUi();
  
  const message = `
API URL: ${API_BASE_URL}
API Key: ${API_SECRET_KEY.substring(0, 8)}...

Чтобы изменить настройки:
1. Откройте Apps Script (Расширения -> Apps Script)
2. Измените константы API_BASE_URL и API_SECRET_KEY
3. Сохраните изменения (Ctrl+S)
  `.trim();
  
  ui.alert('⚙️ Настройки API', message, ui.ButtonSet.OK);
}


/**
 * Форматирование даты/времени
 */
function formatDateTime(isoString) {
  if (!isoString) return 'N/A';
  
  try {
    const date = new Date(isoString);
    return Utilities.formatDate(date, 'Europe/Moscow', 'dd.MM.yyyy HH:mm:ss');
  } catch (e) {
    return isoString;
  }
}


/**
 * Триггер для автоматического запуска (опционально)
 * Настроить в: Apps Script -> Триггеры -> Добавить триггер
 * 
 * Пример: запуск каждый час с 9:00 до 21:00
 */
function scheduledTrigger() {
  const hour = new Date().getHours();
  
  // Проверка времени (9:00 - 21:00 МСК)
  if (hour >= 9 && hour <= 21) {
    try {
      // Проверяем, не выполняется ли уже парсер
      const url = `${API_BASE_URL}/status`;
      const options = {
        method: 'get',
        headers: {
          'Authorization': `Bearer ${API_SECRET_KEY}`
        },
        muteHttpExceptions: true
      };
      
      const result = UrlFetchApp.fetch(url, options);
      const response = JSON.parse(result.getContentText());
      
      // Если не выполняется - запускаем
      if (!response.data.is_running) {
        triggerParserSilent();
      }
    } catch (error) {
      Logger.log('Scheduled trigger error: ' + error);
    }
  }
}


/**
 * Тихий запуск парсера (без UI, для триггеров)
 */
function triggerParserSilent() {
  try {
    const url = `${API_BASE_URL}/trigger`;
    const payload = {
      source: 'app_script_scheduled',
      force: false
    };
    
    const options = {
      method: 'post',
      contentType: 'application/json',
      headers: {
        'Authorization': `Bearer ${API_SECRET_KEY}`
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    
    const result = UrlFetchApp.fetch(url, options);
    Logger.log(`Parser triggered: ${result.getResponseCode()}`);
    
  } catch (error) {
    Logger.log('Error triggering parser silently: ' + error);
  }
}
