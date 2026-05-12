# 🚀 Project Stretch Goals & Hardening Roadmap

This document outlines the planned enhancements and architectural hardening for the Transaction Risk Gateway.

## 🏗️ Architectural Hardening
- [ ] **Infrastructure as Code**: Add Terraform scripts for AWS/GCP deployment.
- [ ] **Redis Caching Layer**: Cache user profiles and recent transaction velocity to reduce database load.
- [ ] **Message Queue**: Implement Celery/RabbitMQ for asynchronous audit logging to prevent API latency.

## 🔒 Security & Compliance
- [ ] **API Security**: Add OAuth2/JWT authentication for all endpoints.
- [ ] **Rate Limiting**: Implement per-user and per-IP rate limiting using SlowAPI/Redis.
- [ ] **Data Masking**: Ensure PII in audit logs is masked or encrypted at rest.

## 🤖 AI & ML Enhancements
- [ ] **Model Monitoring**: Implement drift detection for the scikit-learn anomaly model.
- [ ] **A/B Testing**: Support multiple decision engine versions running in parallel (shadow mode).
- [ ] **Feedback Loop**: Enable human reviewers to "tag" decisions to create a new training set for model retraining.

## 🛠️ Operational Excellence
- [ ] **Health Checks**: Add `/health` and `/ready` probes for Kubernetes.
- [ ] **CI/CD Pipeline**: Setup GitHub Actions for automated testing and linting.
- [ ] **Dashboard**: Build a Streamlit-based monitoring dashboard for real-time risk visualization.
