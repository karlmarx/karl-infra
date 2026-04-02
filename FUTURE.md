# Roadmap

## Short Term (Active)

### find-hub-tracker
- [ ] Deploy to ultra.cc seedbox (deploy script + systemd service ready)
- [x] Set up Healthchecks.io dead man's switch ([#4](https://github.com/karlmarx/find-hub-tracker/issues/4)) — PR #5 merged
- [x] Build end-to-end: Google Find Hub API -> PostgreSQL -> Discord alerts

### claude-pipeline
- [ ] Test end-to-end with real prompt file
- [ ] Confirm Nextcloud -> inbox/ -> OpenClaw flow

### TrickAdvisor
- [ ] Profile editing: bio, display name, preferences ([#7](https://github.com/karlmarx/TrickAdvisor/issues/7))
- [ ] Fix rating subcategory 500 errors
- [ ] Empty states and loading skeletons ([#9](https://github.com/karlmarx/TrickAdvisor/issues/9))
- [ ] Post-registration onboarding ([#10](https://github.com/karlmarx/TrickAdvisor/issues/10))
- [ ] Alternative rating icon: loads scale ([#6](https://github.com/karlmarx/TrickAdvisor/issues/6))
- [ ] Add mock/seed test data ([#5](https://github.com/karlmarx/TrickAdvisor/issues/5))

### nwb-plan
- [x] Migrate from single-file HTML to Next.js 16 + React 19 + TypeScript ([#21](https://github.com/karlmarx/nwb-plan/issues/21))
- [x] Claude API integration for AI exercise suggestions
- [x] Equipment-aware superset system with nearby picker
- [x] Expand to 67+ exercises with 35+ animated SVG diagrams
- [ ] About modal with disclaimer ([#34](https://github.com/karlmarx/nwb-plan/issues/34))
- [ ] Visual regression testing in deployment pipeline ([#31](https://github.com/karlmarx/nwb-plan/issues/31))

### blazing-paddles-react
- [ ] Remove YouTube links ([#15](https://github.com/karlmarx/blazing-paddles-react/issues/15))
- [ ] Clean up DatePicker.tsx ([#14](https://github.com/karlmarx/blazing-paddles-react/issues/14))
- [ ] Fix package.json homepage ([#12](https://github.com/karlmarx/blazing-paddles-react/issues/12))
- [ ] Rewrite api/ical.py ([#10](https://github.com/karlmarx/blazing-paddles-react/issues/10))

## Medium Term

### Infrastructure
- [ ] Evaluate 2018 MacBook as home automation server ([find-hub-tracker#1](https://github.com/karlmarx/find-hub-tracker/issues/1))
- [ ] Design shared schema for multi-service automation platform ([find-hub-tracker#2](https://github.com/karlmarx/find-hub-tracker/issues/2))
- [ ] Migrate periodic automation tasks from Windows WSL to dedicated infra ([find-hub-tracker#3](https://github.com/karlmarx/find-hub-tracker/issues/3))

### TrickAdvisor (Feature Backlog)
- [ ] Notifications: encounter requests, photo status, new ratings ([#11](https://github.com/karlmarx/TrickAdvisor/issues/11))
- [ ] Mobile UX: swipe gestures, haptic feedback, pull-to-refresh ([#12](https://github.com/karlmarx/TrickAdvisor/issues/12))
- [ ] Shareable rating card image ([#13](https://github.com/karlmarx/TrickAdvisor/issues/13))
- [ ] Accessibility audit ([#14](https://github.com/karlmarx/TrickAdvisor/issues/14))
- [ ] Improve search: ratings preview, photos in results ([#8](https://github.com/karlmarx/TrickAdvisor/issues/8))

### nwb-plan (Feature Backlog)
- [ ] Workout log ([#15](https://github.com/karlmarx/nwb-plan/issues/15))
- [ ] Volume tracker ([#16](https://github.com/karlmarx/nwb-plan/issues/16))
- [ ] Cross-education progress tracker ([#17](https://github.com/karlmarx/nwb-plan/issues/17))
- [ ] Phase timeline widget ([#18](https://github.com/karlmarx/nwb-plan/issues/18))
- [ ] Share workout ([#19](https://github.com/karlmarx/nwb-plan/issues/19))
- [ ] Dark/light theme toggle ([#20](https://github.com/karlmarx/nwb-plan/issues/20))
- [ ] Migrate from single-file HTML to Vite + React ([#21](https://github.com/karlmarx/nwb-plan/issues/21))

## Long Term

- [ ] amex-claims-automator: automate Amex purchase protection claims end-to-end
- [ ] Home Assistant integration for device tracking
- [ ] Multi-service automation platform (centralized Postgres, shared scheduling)
- [ ] Centralized logging/monitoring across all services
