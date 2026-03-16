// api/build.js — Vercel Serverless Function
// POST /api/build → trigger GitHub Actions → return run_id

module.exports = async function(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST')   return res.status(405).json({ error: 'POST only' });

  const TOKEN = process.env.GITHUB_TOKEN;
  const OWNER = process.env.GITHUB_OWNER;
  const REPO  = process.env.GITHUB_REPO || 'app5web-builder';

  if (!TOKEN || !OWNER) return res.status(500).json({
    error: 'Server belum dikonfigurasi. Set GITHUB_TOKEN dan GITHUB_OWNER di Vercel env vars.'
  });

  let body = req.body;
  if (typeof body === 'string') { try { body = JSON.parse(body); } catch { return res.status(400).json({ error: 'Invalid JSON' }); } }
  if (!body?.app_url || !body?.app_name) return res.status(400).json({ error: 'app_url dan app_name wajib diisi' });

  const pkg = (body.package_id || 'com.app5web.myapp').replace(/[^a-z0-9.]/gi,'').toLowerCase();

  try {
    // Trigger workflow_dispatch
    const r = await fetch(`https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/build-apk.yml/dispatches`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${TOKEN}`,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ref: 'main',
        inputs: {
          app_name:        String(body.app_name),
          app_url:         String(body.app_url),
          package_id:      pkg,
          app_version:     String(body.app_version     || '1.0.0'),
          version_code:    String(body.version_code    || '1'),
          color_primary:   String(body.color_primary   || '#3b82f6').replace('#',''),
          color_accent:    String(body.color_accent    || '#8b5cf6').replace('#',''),
          color_bg:        String(body.color_bg        || '#ffffff').replace('#',''),
          splash_text:     String(body.splash_text     || 'Loading...'),
          splash_duration: String(body.splash_duration || '2000'),
          enable_js:       String(body.enable_js       !== false),
          enable_zoom:     String(body.enable_zoom     !== false),
          enable_offline:  String(body.enable_offline  === true),
          enable_geo:      String(body.enable_geo      === true),
          enable_camera:   String(body.enable_camera   === true),
          permissions:     Array.isArray(body.permissions) ? body.permissions.join(',') : String(body.permissions||'INTERNET'),
          min_sdk:         String(body.min_sdk    || '23'),
          target_sdk:      String(body.target_sdk || '33'),
          orientation:     String(body.orientation || 'unspecified'),
        }
      })
    });

    if (!r.ok) {
      const txt = await r.text();
      return res.status(502).json({ error: `GitHub API error ${r.status}`, detail: txt });
    }

    // Wait 4s then grab latest run ID
    await new Promise(x => setTimeout(x, 4000));
    const runs = await fetch(
      `https://api.github.com/repos/${OWNER}/${REPO}/actions/runs?per_page=3&event=workflow_dispatch`,
      { headers: { 'Authorization': `Bearer ${TOKEN}`, 'Accept': 'application/vnd.github+json' } }
    );
    const runData = runs.ok ? await runs.json() : {};
    const latest  = runData.workflow_runs?.[0];

    return res.status(200).json({
      success:      true,
      run_id:       latest?.id || null,
      run_url:      latest?.html_url || null,
      github_owner: OWNER,
      github_repo:  REPO,
    });

  } catch(e) {
    return res.status(500).json({ error: String(e.message) });
  }
};
