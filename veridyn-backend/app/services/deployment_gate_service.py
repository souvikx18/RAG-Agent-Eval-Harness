from app.models.deployment_gate import DeploymentGate
from app.models.evaluation import Evaluation
from sqlalchemy.orm import Session


def calculate_deployment_decision(
    evaluation: Evaluation,
    overall_score: float,
) -> DeploymentGate:

    if overall_score >= 0.80:
        decision = "PASS"
        reason = "Evaluation score meets the deployment threshold."

    elif overall_score >= 0.50:
        decision = "REVIEW"
        reason = "Evaluation score requires manual review."

    else:
        decision = "BLOCK"
        reason = "Evaluation score is below the deployment threshold."

    return DeploymentGate(
        evaluation_id=evaluation.id,
        decision=decision,
        overall_score=overall_score,
        reason=reason,
    )


def create_deployment_gate(
    evaluation: Evaluation,
    overall_score: float,
    db: Session,
) -> DeploymentGate:

    existing_gate = (
        db.query(DeploymentGate)
        .filter(
            DeploymentGate.evaluation_id == evaluation.id
        )
        .first()
    )

    if existing_gate:
        return existing_gate

    gate = calculate_deployment_decision(
        evaluation,
        overall_score,
    )

    db.add(gate)
    db.commit()
    db.refresh(gate)

    return gate