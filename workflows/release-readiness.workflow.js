export const meta = {
  name: 'release-readiness',
  description: 'Adversarially verify a local release branch before opening its draft pull request',
  phases: [
    { title: 'Independent audits', detail: 'Inspect repository state and implementation evidence from separate lenses' },
    { title: 'Fresh-context gate', detail: 'Issue a refute-by-default publication decision' },
  ],
  whenToUse: 'Before publishing a completed implementation branch as a pull request',
}

const AUDIT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    verdict: { type: 'string', enum: ['supported', 'unsupported', 'blocked'] },
    confirmedEvidence: { type: 'array', items: { type: 'string' } },
    weakeningEvidence: { type: 'array', items: { type: 'string' } },
    blockingIssues: { type: 'array', items: { type: 'string' } },
    uncertainty: { type: 'array', items: { type: 'string' } },
  },
  required: ['verdict', 'confirmedEvidence', 'weakeningEvidence', 'blockingIssues', 'uncertainty'],
}

const GATE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    decision: { type: 'string', enum: ['create_draft_pr', 'do_not_publish'] },
    rationale: { type: 'string' },
    blockingIssues: { type: 'array', items: { type: 'string' } },
    confirmedEvidence: { type: 'array', items: { type: 'string' } },
    residualUncertainty: { type: 'array', items: { type: 'string' } },
    requiredPrNotes: { type: 'array', items: { type: 'string' } },
  },
  required: ['decision', 'rationale', 'blockingIssues', 'confirmedEvidence', 'residualUncertainty', 'requiredPrNotes'],
}

const contract = {
  objective: 'Determine whether the requested price-action stock selector branch is ready for a public draft PR.',
  nonGoals: ['Modify files', 'Merge the branch', 'Claim real IBKR connectivity without a live TWS session', 'Claim Docker runtime validation when Docker is unavailable'],
  allowedActions: ['Read repository files', 'Run read-only git inspection commands', 'Inspect implementation and test definitions'],
  forbiddenActions: ['Write files', 'Change git state', 'Push', 'Open or merge a PR', 'Expose credentials'],
  successCriteria: ['Head commit and branch match the requested release', 'Diff contains the promised MVP', 'No tracked secrets or generated runtime data', 'Known validation gaps are disclosed'],
  failureCriteria: ['Missing core modules', 'Dirty or divergent release state', 'Tracked credentials', 'Unsupported completion claims'],
  sandbox: 'read-only',
}

phase('Independent audits')
const audits = await parallel([
  () => agent(
    `You are the Release Artifact Auditor. Work in ${args.projectPath}.\n` +
    `Contract: ${JSON.stringify(contract)}\n` +
    `Expected repository: ${args.repository}; base=${args.baseBranch}; head=${args.headBranch}.\n` +
    `Inspect git status, branches, tracking refs, commit graph, base..head diff statistics, tracked file list, .gitignore, and remote URL. ` +
    `Look specifically for credentials, databases, caches, node_modules, dist output, or unrelated legacy files. ` +
    `Default to unsupported if local evidence cannot prove a claim. Return only structured evidence.`,
    { label: 'artifact-auditor', phase: 'Independent audits', schema: AUDIT_SCHEMA, sandbox: 'read-only', cwd: args.projectPath },
  ),
  () => agent(
    `You are the Implementation and Reproducibility Auditor. Work in ${args.projectPath}.\n` +
    `Contract: ${JSON.stringify(contract)}\n` +
    `Claimed validation ledger: ${JSON.stringify(args.validationLedger)}.\n` +
    `Inspect the backend, frontend, infrastructure, knowledge index, README, and tests. Verify that the repository visibly implements ` +
    `IBKR read-only daily data, eight explainable rules, scanner, chart annotations, backtest, database models, demo mode, and documented limitations. ` +
    `Do not treat the claimed ledger as self-proving; distinguish inspectable evidence from unverified runtime claims. ` +
    `Default to blocked for any critical missing component or misleading claim. Return only structured evidence.`,
    { label: 'implementation-auditor', phase: 'Independent audits', schema: AUDIT_SCHEMA, sandbox: 'read-only', cwd: args.projectPath },
  ),
])

phase('Fresh-context gate')
const gate = await agent(
  `You are the independent Publication Gate. You did not produce either audit.\n` +
  `Task contract: ${JSON.stringify(contract)}\n` +
  `Release request: create a public draft PR from ${args.headBranch} into ${args.baseBranch} in ${args.repository}.\n` +
  `Independent audits: ${JSON.stringify(audits)}\n` +
  `Rule: decide do_not_publish if an audit is null, blocked, contains a critical blocking issue, or the branch/commit cannot be established. ` +
  `A disclosed limitation such as no local Docker CLI or no live TWS session is not a blocker when the PR accurately states it. ` +
  `List the exact notes the PR must preserve. Return only the strict gate object.`,
  { label: 'publication-gate', phase: 'Fresh-context gate', schema: GATE_SCHEMA, sandbox: 'read-only', cwd: args.projectPath },
)

return { contract, audits, gate }
