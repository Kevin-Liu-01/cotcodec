import { parseAst } from '/Users/kevinliu/repos/Relay/node_modules/rolldown/dist/parse-ast-index.mjs';
import { readFileSync } from 'node:fs';
const file = process.argv[2];
const src = readFileSync(file, 'utf8');
const ast = parseAst(src, { lang: 'jsx' });
const out = { jsxText: [], attr: [], exprStr: [], template: [] };
const ATTRS = new Set(['aria-label','title','placeholder','alt','aria-description','aria-roledescription','label']);
function walk(n, parent, inJsxExpr) {
  if (!n || typeof n !== 'object') return;
  if (Array.isArray(n)) { for (const c of n) walk(c, parent, inJsxExpr); return; }
  if (n.type === 'JSXText') { const t = n.value.trim(); if (t && /[A-Za-z]/.test(t)) out.jsxText.push(t); }
  if (n.type === 'JSXAttribute') {
    const name = n.name?.name;
    if (ATTRS.has(name)) {
      if (n.value?.type === 'Literal' && typeof n.value.value === 'string') out.attr.push(name + '=' + n.value.value);
      else if (n.value?.type === 'JSXExpressionContainer') out.attr.push(name + '={expr}');
    }
  }
  if (n.type === 'JSXExpressionContainer') {
    for (const k in n) if (k !== 'type') walk(n[k], n, true);
    return;
  }
  if (inJsxExpr && n.type === 'Literal' && typeof n.value === 'string' && /[A-Za-z]{2}/.test(n.value) && / /.test(n.value)) out.exprStr.push(n.value);
  if (inJsxExpr && n.type === 'TemplateLiteral') out.template.push(n.quasis.map(q=>q.value.cooked).join('${}'));
  for (const k in n) if (k !== 'type' && k!=='start' && k!=='end') walk(n[k], n, inJsxExpr);
}
walk(ast, null, false);
const uniq = (a) => [...new Set(a)];
console.log(JSON.stringify({ file, jsxText: out.jsxText.length, jsxTextUniq: uniq(out.jsxText).length, attrs: out.attr.length, attrsUniq: uniq(out.attr).length, attrExpr: out.attr.filter(a=>a.endsWith('{expr}')).length, exprStrings: uniq(out.exprStr).length, templates: uniq(out.template).length }, null, 0));
if (process.argv[3]==='-v') { console.log(uniq(out.jsxText).slice(0,400).join(' | ')); console.log('ATTRS', uniq(out.attr).join(' | ')); console.log('EXPR', uniq(out.exprStr).slice(0,200).join(' | ')); console.log('TPL', uniq(out.template).join(' | ')); }
