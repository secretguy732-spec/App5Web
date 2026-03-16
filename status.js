// api/status.js — Vercel Serverless Function
// GET /api/status?run_id=xxx → return build status + download URL

module.exports = async function(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const TOKEN = process.env.GITHUB_TOKEN;
  const OWNER = process.env.GITHUB_OWNER;
  const REPO  = process.env.GITHUB_REPO || 'app5web-builder';
  const { run_id } = req.query || {};
  if (!run_id) return res.status(400).json({ error: 'run_id required' });

  const H = {
    'Authorization': `Bearer ${TOKEN}`,
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
  };

  try {
    const runRes  = await fetch(`https://api.github.com/repos/${OWNER}/${REPO}/actions/runs/${run_id}`, { headers: H });
    if (!runRes.ok) return res.status(502).json({ error: 'Cannot fetch run status' });
    const run = await runRes.json();

    let label = run.status, percent = 5;
    if (run.status === 'queued')      { label = 'Menunggu runner GitHub...'; percent = 8; }
    if (run.status === 'in_progress') { label = 'Sedang build APK...';       percent = 40;
      // Get step detail
      try {
        const jr = await fetch(`https://api.github.com/repos/${OWNER}/${REPO}/actions/runs/${run_id}/jobs`, { headers: H });
        if (jr.ok) {
          const jd   = await jr.json();
          const job  = jd.jobs?.[0];
          const step = job?.steps?.find(s => s.status === 'in_progress');
          const done = job?.steps?.filter(s => s.status === 'completed').length || 0;
          const tot  = job?.steps?.length || 10;
          if (step) { label = step.name; percent = Math.round(10 + (done/tot)*82); }
        }
      } catch(_) {}
    }
    if (run.status === 'completed') {
      percent = 100;
      label   = run.conclusion === 'success' ? '✓ APK berhasil dibuild!' : `✗ Build gagal (${run.conclusion})`;
    }

    // Get download URL if done
    let download_url = null;
    if (run.status === 'completed' && run.conclusion === 'success') {
      try {
        const rr = await fetch(`https://api.github.com/repos/${OWNER}/${REPO}/releases?per_page=3`, { headers: H });
        if (rr.ok) {
          const rels = await rr.json();
          for (const rel of rels) {
            const apk = rel.assets?.find(a => a.name.endsWith('.apk'));
            if (apk) { download_url = apk.browser_download_url; break; }
          }
          if (!download_url && rels[0]) download_url = rels[0].html_url;
        }
      } catch(_) {}
      if (!download_url) download_url = `https://github.com/${OWNER}/${REPO}/actions/runs/${run_id}`;
    }

    return res.status(200).json({
      status:       run.status,
      conclusion:   run.conclusion || null,
      label, percent,
      html_url:     run.html_url,
      download_url,
    });
  } catch(e) {
    return res.status(500).json({ error: String(e.message) });
  }
};
