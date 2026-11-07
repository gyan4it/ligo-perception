// page_margin_probe.js — CSS @page margin inspection via CSSOM
// Contract: arrow function taking opts, returning
//   { page_rules: [...], errors: [...], cssom_accessible: boolean,
//     all_margins_found: boolean, total_page_rules: number,
//     total_errors: number }
// Violation codes: MARGIN-MISMATCH, MARGIN-MISSING, MARGIN-NOT-VERIFIABLE, E00
// Options: { expected_margins_mm: { top, right, bottom, left }, tolerance_mm }
// The runner always calls it:  ( <source> )({...})
(opts) => {
  const issues = [];
  const page_rules = [];
  const errors = [];
  let cssom_accessible = false;
  const expected = (opts && opts.expected_margins_mm) || {};
  const tolerance_mm = (opts && opts.tolerance_mm !== undefined)
    ? opts.tolerance_mm : 0.5;

  const parse_css_value = (val) => {
    const m = val.trim().match(/^([+-]?[\d.]+)\s*(cm|mm|in|pt|px|%|)$/i);
    if (!m) return { raw: val, unit: 'unknown', value_mm: null };
    const num = parseFloat(m[1]);
    const unit = (m[2] || '').toLowerCase();
    const value_mm = convert_to_mm(num, unit);
    return { num, unit, value_mm: value_mm !== null ? value_mm : null,
      raw: val };
  };

  const convert_to_mm = (value, unit) => {
    switch (unit) {
      case 'mm': return value;
      case 'cm': return value * 10;
      case 'in': return value * 25.4;
      case 'pt': return value * 25.4 / 72;
      case 'px': return value * 25.4 / 96;
      case '%': return null;
      case '': return null;
      default: return null;
    }
  };

  try {
    const sheets = document.styleSheets;
    cssom_accessible = true;

    for (let i = 0; i < sheets.length; i++) {
      let rules = null;
      try {
        rules = sheets[i].cssRules || sheets[i].rules;
      } catch (e) {
        errors.push({
          sheet_index: i,
          sheet_href: sheets[i].href || '(inline)',
          error: e.message || String(e),
          code: 'SHEET-INACCESSIBLE'
        });
        continue;
      }

      if (!rules) continue;

      for (let j = 0; j < rules.length; j++) {
        const rule = rules[j];

        const isPageRule = rule.type === 6 ||
          (rule.type === undefined && rule.cssText &&
            rule.cssText.trim().startsWith('@page'));

        if (isPageRule) {
          const page_rule = {
            selector: rule.selectorText || '@page',
            margin: {},
            raw_css_text: rule.cssText,
            source_sheet_index: i,
            source_sheet_href: sheets[i].href || '(inline)'
          };

          const margin_props = ['margin', 'margin-top', 'margin-right',
            'margin-bottom', 'margin-left'];
          for (const prop of margin_props) {
            const val = rule.style.getPropertyValue(prop);
            if (val && val.trim()) {
              page_rule.margin[prop] = parse_css_value(val);
            }
          }

          page_rules.push(page_rule);
        }
      }
    }
  } catch (e) {
    cssom_accessible = false;
    errors.push({
      error: e.message || String(e),
      code: 'CSSOM-ERROR'
    });
  }

  const margin_props_set = new Set();
  for (const pr of page_rules) {
    for (const prop of Object.keys(pr.margin)) {
      margin_props_set.add(prop);
    }
  }
  const all_margins_found = ['margin', 'margin-top', 'margin-right',
    'margin-bottom', 'margin-left'].some(p => margin_props_set.has(p));

  return {
    page_rules,
    errors,
    cssom_accessible,
    all_margins_found,
    total_page_rules: page_rules.length,
    total_errors: errors.length,
    expected_margins_mm: expected,
    tolerance_mm
  };
}
