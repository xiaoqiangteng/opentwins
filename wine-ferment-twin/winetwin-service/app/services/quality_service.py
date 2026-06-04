from app.services.rules import evaluate


def quality_summary(attributes, features, alarm_rules):
    result = evaluate(attributes, features, alarm_rules)
    return {
        "quality_score": result["quality_score"],
        "risk_level": result["risk_level"],
        "stage": result["stage"],
    }

