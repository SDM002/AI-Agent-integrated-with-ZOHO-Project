import { BACKEND_URL } from '@/lib/config';

export default function handler(req, res) {
  // Ensure we have a backend URL
  if (!BACKEND_URL) {
    res.status(500).json({ error: 'BACKEND_URL not configured' });
    return;
  }
  // Convert http(s) to ws(s)
  const wsBase = BACKEND_URL.replace(/^https?:\/\//, (m) => (m === 'https://' ? 'wss://' : 'ws://'));
  // Trim any trailing slash
  const cleanWsBase = wsBase.replace(/\/+$/, '');
  res.status(200).json({ wsUrl: cleanWsBase });
}
