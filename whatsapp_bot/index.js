const fs = require('fs');
const path = require('path');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

// ─── Config loader ───────────────────────────────────────────────────────────
function loadConfig() {
  const configPath = path.join(__dirname, '..', 'config', 'settings.json');
  try {
    return JSON.parse(fs.readFileSync(configPath, 'utf-8'));
  } catch {
    return {};
  }
}

const config = loadConfig();
const botCfg = config.whatsapp_bot || {};
const webhookUrl = `http://127.0.0.1:${botCfg.webhook_port || 5001}`;
const monitoredGroups = botCfg.monitored_groups || [];

// Keywords that suggest a message is a job vacancy
const VACANCY_KEYWORDS = [
  'hiring', 'vacancy', 'job', 'position', 'opening', 'recruiting',
  'requirement', 'we need', 'looking for', 'urgent hiring',
  'work from home', 'remote', 'office based', 'full time', 'part time',
  'internship', 'contract', 'salary', 'stipend', 'experience',
  'qualification', 'applying', 'candidate',
];

function looksLikeVacancy(text) {
  const lower = text.toLowerCase();
  let score = 0;
  for (const kw of VACANCY_KEYWORDS) {
    if (lower.includes(kw)) score++;
  }
  return score >= 2;  // at least 2 keywords to avoid false positives
}

// ─── WhatsApp client ─────────────────────────────────────────────────────────
const client = new Client({
  authStrategy: new LocalAuth({
    dataPath: botCfg.session_path || './whatsapp_session',
  }),
  puppeteer: {
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  },
});

client.on('qr', (qr) => {
  console.log('\n📱 Scan this QR code with WhatsApp:\n');
  qrcode.generate(qr, { small: true });
  console.log('\n');
});

client.on('ready', () => {
  console.log('✅ WhatsApp bot connected successfully');
});

client.on('authenticated', () => {
  console.log('🔐 Session authenticated');
});

client.on('auth_failure', (msg) => {
  console.error('❌ Auth failure:', msg);
});

client.on('disconnected', (reason) => {
  console.log('⚠️ Disconnected:', reason);
});

// ─── Message handler ─────────────────────────────────────────────────────────
client.on('message', async (msg) => {
  try {
    // Only handle group messages
    const chat = await msg.getChat();
    if (!chat.isGroup) return;

    const groupName = chat.name;
    const groupId = chat.id._serialized;

    // If specific groups are configured, only process those
    if (monitoredGroups.length > 0 && !monitoredGroups.includes(groupName) && !monitoredGroups.includes(groupId)) {
      return;
    }

    // Skip commands and media-only messages
    if (!msg.body || msg.body.startsWith('!') || msg.body.startsWith('/')) return;

    const text = msg.body.trim();
    if (!text || !looksLikeVacancy(text)) return;

    const sender = msg.author || msg.from;
    console.log(`🔍 Vacancy detected in "${groupName}" from ${sender}`);

    // Reply with a processing indicator
    await msg.reply('⏳ Processing vacancy message...');

    // Send to Python webhook
    const response = await axios.post(`${webhookUrl}/webhook/process-vacancy`, {
      message: text,
      group_name: groupName,
      sender: sender,
    }, { timeout: 120000 });

    const result = response.data;
    if (!result.success) {
      await msg.reply(`❌ Error: ${result.error}`);
      return;
    }

    // Send summary
    await msg.reply(result.summary);

    // Send poster image if available
    if (result.poster_image) {
      try {
        const imgResp = await axios.get(result.poster_image, {
          responseType: 'arraybuffer',
          timeout: 30000,
        });
        const media = new MessageMedia(
          'image/jpeg',
          Buffer.from(imgResp.data).toString('base64'),
          `vacancy_${result.vacancy_id}.jpg`
        );
        await msg.reply(media, undefined, { caption: `🎨 Poster for Vacancy #${result.vacancy_id}` });
      } catch (imgErr) {
        console.warn('Could not send poster image:', imgErr.message);
        // Fallback: send the URL
        await msg.reply(`🖼️ Poster: ${result.poster_image}`);
      }
    }

    // Check if Facebook is configured and ask to publish
    const fbCfg = config.facebook || {};
    if (fbCfg.access_token && fbCfg.group_ids && fbCfg.group_ids.length > 0) {
      try {
        const fbResult = await axios.post(`${webhookUrl}/webhook/publish-facebook`, {
          vacancy_id: result.vacancy_id,
        }, { timeout: 60000 });

        const fbData = fbResult.data;
        if (fbData.success) {
          for (const r of fbData.results) {
            if (r.success) {
              await msg.reply(`📤 Published to Facebook: ${r.post_id}`);
            } else {
              await msg.reply(`❌ Facebook publish failed: ${r.error}`);
            }
          }
        }
      } catch (fbErr) {
        console.warn('Facebook publish error:', fbErr.message);
      }
    }

    console.log(`✅ Vacancy #${result.vacancy_id} processed and replied in "${groupName}"`);

  } catch (err) {
    console.error('Message handler error:', err);
    try {
      await msg.reply('❌ Sorry, something went wrong processing this vacancy.');
    } catch { /* ignore */ }
  }
});

// ─── Health check: verify webhook is reachable ──────────────────────────────
async function checkWebhook() {
  try {
    const resp = await axios.get(`${webhookUrl}/webhook/health`, { timeout: 5000 });
    if (resp.data.status === 'ok') {
      console.log(`✅ Python webhook reachable at ${webhookUrl}`);
    }
  } catch {
    console.warn(`⚠️  Python webhook not reachable at ${webhookUrl}. Make sure webhook.py is running.`);
  }
}

// ─── Start ───────────────────────────────────────────────────────────────────
console.log('🚀 Ghost WhatsApp Bot starting...');
checkWebhook();
client.initialize();
