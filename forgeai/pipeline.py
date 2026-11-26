"""
ForgeAI Main Pipeline
======================
The master orchestrator that runs the complete agent factory pipeline:
1. Intake Interview → 2. Groundability Guard → 3. Agent Generation →
4. Eval Generation → 5. Judging → 6. Critic-Optimizer Loop →
7. Honest Reporting → 8. Runnable Product → 9. Demo Runs

Also implements stretch goals:
- Prompt Tournament
- Budget Enforcement
- Human Checkpoint
"""

import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from forgeai.config import ForgeAIConfig, get_llm, get_embeddings
from forgeai.models import (
    RequirementsDocument, AgentDefinition, EvalSet,
    IterationScorecard, OptimizationLog, ForgeAIReport, CaseScore
)
from forgeai.core.document_processor import (
    load_documents, chunk_documents, create_vector_store, get_document_summary
)
from forgeai.core.interviewer import IntakeInterviewer
from forgeai.core.agent_generator import AgentGenerator
from forgeai.core.eval_generator import EvalGenerator
from forgeai.core.judge import Judge
from forgeai.core.optimizer import CriticOptimizer
from forgeai.tools.registry import ToolRegistry
from forgeai.runners.agent_runner import AgentRunner
from forgeai.utils.report_generator import generate_report


class ForgeAIPipeline:
    """
    The Agent Factory — the machine that builds, tests, and ships agents.
    
    This is the main orchestrator that ties together all nine core requirements
    plus the stretch goals.
    """

    def __init__(self, config: ForgeAIConfig = None):
        self.config = config or ForgeAIConfig()
        self.console = Console()
        self.tool_registry = ToolRegistry()

        # Pipeline components
        self.interviewer = IntakeInterviewer(
            self.config.llm, self.tool_registry.available_tools
        )
        self.generator = AgentGenerator(
            self.config.llm, self.tool_registry.available_tools
        )
        self.eval_generator = EvalGenerator(self.config.llm)
        self.judge = Judge(self.config.llm)
        self.optimizer = CriticOptimizer(self.config.llm, self.config.budget)

    def run(
        self,
        brief: str,
        doc_folder: str,
        output_dir: str = "output",
        auto_mode: bool = True,
        human_checkpoint: bool = False,
        run_tournament: bool = True,
        clarifications: Optional[List[dict]] = None
    ) -> ForgeAIReport:
        """
        Run the complete ForgeAI pipeline.
        
        Args:
            brief: One-paragraph description of the desired agent
            doc_folder: Path to folder containing documents
            output_dir: Where to save artifacts
            auto_mode: If True, auto-answer clarifying questions
            human_checkpoint: Stretch goal — pause for human review of requirements
            run_tournament: Stretch goal — run prompt tournament
            clarifications: Pre-provided clarifications (skip interview)
            
        Returns:
            ForgeAIReport with all artifacts
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        self.console.print(Panel(
            f"[bold cyan]ForgeAI Pipeline Starting[/bold cyan]\n\n"
            f"Brief: {brief[:200]}...\n"
            f"Documents: {doc_folder}\n"
            f"Output: {output_dir}\n"
            f"Auto Mode: {auto_mode}\n"
            f"Budget: {self.config.budget.max_tokens_per_run:,} tokens, "
            f"{self.config.budget.max_iterations} iterations",
            title="🏭 ForgeAI",
            border_style="cyan"
        ))

        # ═══════════════════════════════════════════════════════════════
        # STAGE 1 & 2: Intake Interview + Groundability Guard
        # ═══════════════════════════════════════════════════════════════
        self.console.print("\n[bold yellow]━━━ Stage 1 & 2: Intake Interview & Groundability Guard ━━━[/bold yellow]")

        requirements = self.interviewer.build_requirements(
            brief=brief,
            doc_folder=doc_folder,
            clarifications=clarifications,
            auto_mode=auto_mode
        )

        self._display_requirements(requirements)

        # Groundability warnings
        if requirements.groundability_warnings:
            self.console.print(Panel(
                "\n".join(f"⚠️  {w}" for w in requirements.groundability_warnings),
                title="🛡️ Groundability Warnings",
                border_style="yellow"
            ))

        # Human checkpoint (stretch goal)
        if human_checkpoint and not auto_mode:
            self.console.print("\n[bold magenta]Human Checkpoint: Review requirements above.[/bold magenta]")
            proceed = input("Approve and continue? (y/n/edit): ").strip().lower()
            if proceed == "n":
                self.console.print("[red]Pipeline stopped by user.[/red]")
                return self._create_empty_report(requirements)
            elif proceed == "edit":
                # Allow editing (simplified)
                self.console.print("[dim]Editing not implemented in CLI — continuing with current requirements.[/dim]")

        # Save requirements
        (output_path / "requirements.json").write_text(
            requirements.model_dump_json(indent=2), encoding="utf-8"
        )

        # ═══════════════════════════════════════════════════════════════
        # STAGE 3: Agent Generation (+ Prompt Tournament stretch goal)
        # ═══════════════════════════════════════════════════════════════
        self.console.print("\n[bold yellow]━━━ Stage 3: Agent Generation ━━━[/bold yellow]")

        tournament_results = None
        if run_tournament:
            self.console.print("[cyan]Running Prompt Tournament (stretch goal)...[/cyan]")
            candidates = self.generator.generate_tournament(requirements)
            self.console.print(f"[green]Generated {len(candidates)} candidate agents[/green]")

            # We'll evaluate all candidates after creating the eval set
            agent_definition = candidates[0]  # Use first as default, override after tournament
            tournament_candidates = candidates
        else:
            agent_definition = self.generator.generate(requirements)
            tournament_candidates = [agent_definition]

        self._display_agent_definition(agent_definition)

        # ═══════════════════════════════════════════════════════════════
        # STAGE 4: Eval Set Generation
        # ═══════════════════════════════════════════════════════════════
        self.console.print("\n[bold yellow]━━━ Stage 4: Eval Set Generation ━━━[/bold yellow]")

        documents = load_documents(doc_folder)
        doc_samples = [doc.page_content for doc in documents]

        eval_set = self.eval_generator.generate(
            requirements=requirements,
            document_samples=doc_samples,
            num_cases=24
        )

        self.console.print(f"[green]Generated {len(eval_set.cases)} evaluation cases[/green]")
        self._display_eval_summary(eval_set)

        # Save eval set
        (output_path / "eval_set.json").write_text(
            eval_set.model_dump_json(indent=2), encoding="utf-8"
        )

        # ═══════════════════════════════════════════════════════════════
        # Prompt Tournament Evaluation (if enabled)
        # ═══════════════════════════════════════════════════════════════
        if run_tournament and len(tournament_candidates) > 1:
            self.console.print("\n[bold magenta]━━━ Prompt Tournament: Evaluating Candidates ━━━[/bold magenta]")
            tournament_results = self._run_tournament(
                tournament_candidates, eval_set, doc_folder
            )
            # Select winner
            best_idx = max(range(len(tournament_results["candidates"])),
                          key=lambda i: tournament_results["candidates"][i]["score"])
            agent_definition = tournament_candidates[best_idx]
            tournament_results["winner"] = tournament_results["candidates"][best_idx]["name"]
            self.console.print(f"[bold green]🏆 Tournament Winner: {tournament_results['winner']}[/bold green]")

        # ═══════════════════════════════════════════════════════════════
        # STAGE 5 & 6: Judge + Critic-Optimizer Loop
        # ═══════════════════════════════════════════════════════════════
        self.console.print("\n[bold yellow]━━━ Stage 5 & 6: Judge + Critic-Optimizer Loop ━━━[/bold yellow]")

        scorecards: List[IterationScorecard] = []
        optimization_logs: List[OptimizationLog] = []
        current_definition = agent_definition
        previous_score = 0.0

        for iteration in range(self.config.budget.max_iterations + 1):
            self.console.print(f"\n[bold cyan]── Iteration {iteration} ──[/bold cyan]")

            # Build agent runner for this iteration
            chunks = chunk_documents(
                documents,
                chunk_size=current_definition.retrieval_config.chunk_size,
                chunk_overlap=current_definition.retrieval_config.chunk_overlap
            )
            vector_store = create_vector_store(chunks, self.config.embedding)

            # Run all eval cases
            responses = []
            contexts = []
            for case in eval_set.cases:
                try:
                    # Retrieve context
                    retrieved = vector_store.similarity_search(
                        case.question,
                        k=current_definition.retrieval_config.top_k
                    )
                    context_chunks = [doc.page_content for doc in retrieved]

                    # Generate response using the agent
                    runner = AgentRunner(
                        agent_definition=current_definition,
                        llm_config=self.config.llm,
                        embedding_config=self.config.embedding,
                        doc_folder=doc_folder,
                        tool_registry=self.tool_registry
                    )
                    answer, _ = runner.query(case.question)
                    responses.append(answer)
                    contexts.append(context_chunks)
                except Exception as e:
                    responses.append(f"Error: {str(e)}")
                    contexts.append([])

            # Score all cases
            scorecard = self.judge.score_all(
                eval_set.cases, responses, contexts, iteration
            )
            scorecards.append(scorecard)

            self._display_scorecard(scorecard)

            # Check if we should continue optimizing
            if iteration > 0:
                should_continue, reason = self.optimizer.should_continue(
                    scorecard.score, previous_score, iteration
                )
                if not should_continue:
                    self.console.print(f"[yellow]Stopping: {reason}[/yellow]")
                    break

            # Optimize (if not last iteration)
            if iteration < self.config.budget.max_iterations:
                fixes = self.optimizer.analyze_and_prescribe(scorecard, current_definition)

                if fixes:
                    self.console.print(f"[cyan]Applying {len(fixes)} targeted fix(es)...[/cyan]")
                    for fix in fixes:
                        self.console.print(f"  → [{fix.get('change_type', '?')}] {fix.get('description', '')[:100]}")

                    # Apply fixes
                    combined_instruction = "\n".join(
                        fix.get("fix_instruction", "") for fix in fixes
                    )
                    new_definition = self.generator.apply_fix(
                        current_definition,
                        combined_instruction,
                        iteration + 1
                    )

                    # Log optimization
                    for fix in fixes:
                        log = self.optimizer.create_optimization_log(
                            iteration=iteration + 1,
                            fix=fix,
                            score_before=scorecard.score,
                            score_after=0.0  # Will be updated after re-eval
                        )
                        optimization_logs.append(log)

                    scorecard.changes_made = [fix.get("description", "") for fix in fixes]
                    previous_score = scorecard.score
                    current_definition = new_definition

        # Update optimization logs with final scores
        for log in optimization_logs:
            matching_scorecards = [s for s in scorecards if s.iteration == log.iteration]
            if matching_scorecards:
                log.score_after = matching_scorecards[0].score

        # ═══════════════════════════════════════════════════════════════
        # STAGE 7: Honest Reporting
        # ═══════════════════════════════════════════════════════════════
        self.console.print("\n[bold yellow]━━━ Stage 7: Honest Reporting ━━━[/bold yellow]")

        final_scorecard = scorecards[-1] if scorecards else IterationScorecard(
            iteration=0, total_cases=0, passed=0, failed=0, score=0.0
        )

        # Identify known failures
        known_failures = []
        for cs in final_scorecard.case_scores:
            if cs.score < 0.7:
                known_failures.append(
                    f"[{cs.case_id}] ({cs.failure_category.value}): {cs.question} — "
                    f"{cs.failure_explanation}"
                )

        # Generate recommendations
        recommendations = self._generate_recommendations(final_scorecard)

        # Build final report
        report = ForgeAIReport(
            agent_definition=current_definition,
            requirements=requirements,
            eval_set=eval_set,
            scorecards=scorecards,
            optimization_logs=optimization_logs,
            final_score=final_scorecard.score,
            known_failures=known_failures,
            recommendations=recommendations,
            total_tokens_used=self.config.budget.tokens_used,
            total_iterations=len(scorecards),
            prompt_tournament_results=tournament_results
        )

        # Generate and save report
        report_text = generate_report(report, str(output_path))

        self.console.print(Panel(
            f"[bold green]Pipeline Complete![/bold green]\n\n"
            f"Final Score: {report.final_score:.1%}\n"
            f"Iterations: {report.total_iterations}\n"
            f"Known Failures: {len(report.known_failures)}\n"
            f"Artifacts saved to: {output_path}",
            title="✅ ForgeAI Complete",
            border_style="green"
        ))

        return report

    def _run_tournament(
        self,
        candidates: List[AgentDefinition],
        eval_set: EvalSet,
        doc_folder: str
    ) -> Dict[str, Any]:
        """Run prompt tournament across candidate agents."""
        documents = load_documents(doc_folder)
        results = {"candidates": []}

        for i, candidate in enumerate(candidates):
            self.console.print(f"  Evaluating candidate {i+1}: {candidate.name}")

            # Quick evaluation on a subset of cases
            subset = eval_set.cases[:8]  # Use first 8 cases for speed
            chunks = chunk_documents(
                documents,
                chunk_size=candidate.retrieval_config.chunk_size,
                chunk_overlap=candidate.retrieval_config.chunk_overlap
            )
            vector_store = create_vector_store(chunks, self.config.embedding)

            responses = []
            contexts = []
            for case in subset:
                try:
                    retrieved = vector_store.similarity_search(case.question, k=candidate.retrieval_config.top_k)
                    context_chunks = [doc.page_content for doc in retrieved]

                    runner = AgentRunner(
                        agent_definition=candidate,
                        llm_config=self.config.llm,
                        embedding_config=self.config.embedding,
                        doc_folder=doc_folder,
                        tool_registry=self.tool_registry
                    )
                    answer, _ = runner.query(case.question)
                    responses.append(answer)
                    contexts.append(context_chunks)
                except Exception:
                    responses.append("Error generating response")
                    contexts.append([])

            scorecard = self.judge.score_all(subset, responses, contexts, 0)
            results["candidates"].append({
                "name": candidate.name,
                "score": scorecard.score,
                "passed": scorecard.passed,
                "total": scorecard.total_cases
            })
            self.console.print(f"    Score: {scorecard.score:.1%} ({scorecard.passed}/{scorecard.total_cases})")

        return results

    def _display_requirements(self, req: RequirementsDocument):
        """Display requirements in a formatted panel."""
        self.console.print(Panel(
            f"**Scope:** {req.scope}\n"
            f"**Audience:** {req.audience}\n"
            f"**Tone:** {req.tone}\n"
            f"**Must-answer:** {', '.join(req.must_answer_topics[:5])}\n"
            f"**Must-refuse:** {', '.join(req.must_refuse_topics[:5])}\n"
            f"**Tools needed:** {', '.join(req.tools_needed) if req.tools_needed else 'None'}",
            title="📋 Requirements Document",
            border_style="green"
        ))

    def _display_agent_definition(self, defn: AgentDefinition):
        """Display agent definition summary."""
        self.console.print(Panel(
            f"**Name:** {defn.name}\n"
            f"**System Prompt:** {defn.system_prompt[:200]}...\n"
            f"**Tools:** {', '.join(defn.tools) if defn.tools else 'None'}\n"
            f"**Retrieval:** top_k={defn.retrieval_config.top_k}, "
            f"chunk_size={defn.retrieval_config.chunk_size}",
            title="🤖 Agent Definition",
            border_style="blue"
        ))

    def _display_eval_summary(self, eval_set: EvalSet):
        """Display evaluation set summary."""
        type_counts = {}
        for case in eval_set.cases:
            t = case.case_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        table = Table(title="Eval Set Distribution")
        table.add_column("Type", style="cyan")
        table.add_column("Count", justify="right", style="green")
        for t, c in sorted(type_counts.items()):
            table.add_row(t, str(c))
        self.console.print(table)

    def _display_scorecard(self, sc: IterationScorecard):
        """Display a scorecard."""
        bar_len = int(sc.score * 30)
        bar = "█" * bar_len + "░" * (30 - bar_len)

        self.console.print(Panel(
            f"[{'green' if sc.score >= 0.7 else 'yellow' if sc.score >= 0.5 else 'red'}]"
            f"Score: [{bar}] {sc.score:.1%}[/]\n"
            f"Passed: {sc.passed}/{sc.total_cases}  |  Failed: {sc.failed}/{sc.total_cases}\n"
            f"Failures: {', '.join(f'{k}:{v}' for k, v in sc.failure_breakdown.items()) if sc.failure_breakdown else 'None'}",
            title=f"📊 Iteration {sc.iteration} Scorecard",
            border_style="cyan"
        ))

    def _generate_recommendations(self, scorecard: IterationScorecard) -> List[str]:
        """Generate improvement recommendations."""
        recs = []
        if scorecard.failure_breakdown.get("retrieval_miss", 0) > 2:
            recs.append("Consider adding more documents or using a denser chunking strategy")
        if scorecard.failure_breakdown.get("hallucination", 0) > 0:
            recs.append("Strengthen grounding instructions or use a more capable model")
        if scorecard.failure_breakdown.get("wrong_refusal", 0) > 2:
            recs.append("Review scope constraints — the agent may be too restrictive")
        if scorecard.score < 0.6:
            recs.append("Consider providing more comprehensive documents for the topic")
        if not recs:
            recs.append("Agent performs well. Monitor real-world usage for edge cases.")
        return recs

    def _create_empty_report(self, requirements: RequirementsDocument) -> ForgeAIReport:
        """Create an empty report for aborted runs."""
        from forgeai.models import AgentDefinition, EvalSet
        return ForgeAIReport(
            agent_definition=AgentDefinition(
                name="Aborted", system_prompt="Pipeline was stopped."
            ),
            requirements=requirements,
            eval_set=EvalSet(cases=[], generation_prompt="Aborted"),
            final_score=0.0,
            known_failures=["Pipeline was stopped by user before agent generation"]
        )
