from app.services.rules import evaluate


def active_alarms(attributes, features, alarm_rules):
    return evaluate(attributes, features, alarm_rules)["alarms"]

