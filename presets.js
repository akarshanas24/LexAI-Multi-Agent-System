/**
 * presets.js
 * Sample legal case descriptions for quick testing.
 */

const PRESETS = [
  // 0 — IP / Code Theft
  `A senior software engineer at a fintech company resigned and co-founded a competing startup three months later. The former employer alleges the engineer copied 40,000 lines of proprietary source code before leaving and is using it in the new product. The company is seeking $2.5M in damages and an injunction. The engineer claims the code was independently written during personal time, prior to resigning, and that no confidential information was taken.`,

  // 1 — Contract Breach
  `A freelance UX designer delivered a complete brand identity system — logo, typography, color palette, and component library — to an early-stage startup. The contract specified payment of $18,000 upon delivery. The startup accepted the files but refused to pay, alleging the designs did not meet undocumented internal expectations. The designer argues all deliverables matched the signed creative brief and that the client has been using the assets commercially for six weeks.`,

  // 2 — Wrongful Termination
  `An employee with 11 years of tenure and a spotless performance record was terminated without cause eight days after filing a formal HR complaint against her direct manager for creating a hostile work environment. The company maintains the termination was part of a cost-reduction restructuring that affected 12 employees. The employee contends the timing and her unique role make the restructuring justification pretextual, and alleges the termination was direct retaliation for protected activity.`,

  // 3 — Financial Fraud
  `A licensed financial advisor directed six clients to invest a combined $620,000 into a private real-estate fund without disclosing that he personally held a 12% equity stake in the fund's general partner. The clients suffered losses of approximately $410,000 when the fund collapsed. The advisor maintains that a general disclosure clause in the client onboarding agreement covered all potential conflicts of interest, and that his recommendations were made in good faith based on the fund's projected returns.`
];

/**
 * Loads a preset case into the textarea.
 * @param {number} index - Index into PRESETS array
 */
function loadPreset(index) {
  const textarea = document.getElementById('caseInput');
  if (textarea && PRESETS[index] !== undefined) {
    textarea.value = PRESETS[index];
    textarea.focus();
  }
}
