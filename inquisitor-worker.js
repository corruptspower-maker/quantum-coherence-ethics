/**
 * Cloudflare Worker — Grand Inquisitor API proxy.
 *
 * Deploy at: dash.cloudflare.com → Workers → Create Service
 * Set environment variable: ANTHROPIC_API_KEY = sk-ant-...
 *
 * After deploying, update ought.html:
 *   Change API_URL in inquisitor.js from
 *     'https://api.anthropic.com/v1/messages'
 *   to your worker URL, e.g.
 *     'https://inquisitor.YOUR-SUBDOMAIN.workers.dev'
 *
 * The worker keeps your API key out of the browser.
 */

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
        },
      });
    }

    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    var body;
    try { body = await request.json(); } catch(e) {
      return new Response('Bad request', { status: 400 });
    }

    var upstream = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify(body),
    });

    var data = await upstream.json();

    return new Response(JSON.stringify(data), {
      status: upstream.status,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  },
};
