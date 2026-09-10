'use strict';
// Reviewed 2026-09-10. Exact IDs only: new versions need a fresh source review.
// These are comparison candidates, not claims of equivalent performance.
const modelPairings = [
  {
    claude:'claude-fable-5-1', codex:'gpt-5.6-sol', basis:'Published benchmark comparison',
    reason:'Anthropic includes GPT-5.6 Sol in its Fable 5.1 benchmark comparison.',
    sources:['https://www.anthropic.com/claude/fable']
  },
  {
    claude:'claude-fable-5-1', codex:'gpt-6-astra', basis:'Frontier tier (our selection)',
    reason:'Both are positioned for the most demanding reasoning and coding work.',
    sources:['https://platform.claude.com/docs/en/models/overview','https://developers.openai.com/api/docs/models']
  },
  {
    claude:'claude-opus-5', codex:'gpt-5.6-sol', basis:'Complex agentic work (our selection)',
    reason:'Opus targets complex agentic coding; Sol targets complex professional work.',
    sources:['https://platform.claude.com/docs/en/models/overview','https://developers.openai.com/api/docs/models']
  },
  {
    claude:'claude-sonnet-5', codex:'gpt-5.6-terra', basis:'Balanced tier (our selection)',
    reason:'Both balance capability with speed or cost for routine production work.',
    sources:['https://platform.claude.com/docs/en/models/overview','https://developers.openai.com/api/docs/models']
  },
  {
    claude:'claude-haiku-4-5-20251001', codex:'gpt-5.6-luna', basis:'Fast economical tier (our selection)',
    reason:'Haiku emphasizes speed; Luna targets cost-sensitive high-volume work.',
    sources:['https://platform.claude.com/docs/en/models/overview','https://developers.openai.com/api/docs/models']
  }
];
function visibleModelComparisons(points, focus) {
  if (!focus) return [];
  return modelPairings.flatMap(pair=>{
    const from=points.find(p=>p.provider==='claude'&&p.model===pair.claude);
    const to=points.find(p=>p.provider==='codex'&&p.model===pair.codex);
    return from&&to?[{...pair,from,to}]:[];
  });
}
function comparisonArrow(from,to) {
  const dx=to.x-from.x,dy=to.y-from.y,d=Math.hypot(dx,dy);
  if (d<0.001) return null; // Coincident medians have no visible displacement.
  const trim=Math.min(18,d/4),ux=dx/d,uy=dy/d;
  return {x1:from.x+ux*trim,y1:from.y+uy*trim,x2:to.x-ux*trim,y2:to.y-uy*trim};
}
if (typeof module !== 'undefined' && module.exports) module.exports = {modelPairings,visibleModelComparisons,comparisonArrow};
