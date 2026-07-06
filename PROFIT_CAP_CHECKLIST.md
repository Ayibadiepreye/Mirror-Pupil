# ✅ PROFIT CAP - DEPLOYMENT CHECKLIST

**Feature:** Automatic Profit Cap Protection  
**Status:** Ready for deployment  
**Date:** July 6, 2026  

---

## 📦 PRE-DEPLOYMENT VERIFICATION

### Code Quality ✅
- [x] All Python files compile without syntax errors
- [x] All Dart files compile without errors
- [x] All TypeScript files compile without errors
- [x] No circular import issues at runtime
- [x] All edge cases handled
- [x] Comprehensive error handling
- [x] Logging added throughout

### Testing ✅
- [x] Runtime initialization test passed
- [x] Module import chain verified
- [x] Account model fields verified
- [x] Database schema verified
- [x] API endpoints discovered
- [x] Database methods verified
- [x] Risk enforcer methods verified
- [x] Trade executor check verified
- [x] Calculation logic validated
- [x] Edge cases reviewed

### Documentation ✅
- [x] Implementation guide complete
- [x] API reference complete
- [x] Frontend integration guide complete
- [x] Troubleshooting guide complete
- [x] Deployment guide complete
- [x] Bug check results documented

### Database ✅
- [x] Migration SQL created
- [x] Migration applied to Neon PostgreSQL
- [x] All 5 columns verified in database
- [x] Safe defaults set (enabled=false)
- [x] No data loss on existing accounts

---

## 🚀 DEPLOYMENT TASKS

### Backend Deployment
- [ ] SSH into VPS
- [ ] Navigate to project directory
- [ ] Run: `git pull origin main`
- [ ] Restart backend service: `systemctl restart mirror-pupil-backend`
- [ ] Restart telegram service: `systemctl restart mirror-pupil-telegram`
- [ ] Check logs for: "Started profit cap monitoring (10s interval)"
- [ ] Verify no errors in startup logs

### Mobile Deployment (if using Flutter)
- [ ] Navigate to: `Lovable Frontend/export/mobile`
- [ ] Run: `flutter build apk --release` (Android)
- [ ] Or run: `flutter build ios --release` (iOS)
- [ ] Test on device
- [ ] Publish to stores (optional)

### Web Deployment (if using web frontend)
- [ ] Open: `WEB_FRONTEND_INTEGRATION.md`
- [ ] Follow integration steps (5 minutes)
- [ ] Navigate to: `Lovable Frontend`
- [ ] Run: `npm run build`
- [ ] Deploy `dist/` folder to hosting
- [ ] Verify frontend connects to backend API

---

## 🧪 POST-DEPLOYMENT TESTING

### Smoke Tests
- [ ] Backend logs show monitoring started
- [ ] Can access accounts endpoint
- [ ] Mobile/web app loads without errors
- [ ] Can view accounts list

### Feature Testing (Test Account)
- [ ] Create or select test account
- [ ] Configure profit cap (low value for testing)
  - [ ] Type: Dollar or Percentage
  - [ ] Value: Something easily reachable
  - [ ] Buffer: 2%
- [ ] Save settings
- [ ] Verify settings saved (refresh page/app)
- [ ] Monitor logs for cap checks
- [ ] Simulate breach (manual trade to exceed cap)
- [ ] Verify all trades close
- [ ] Verify account freezes
- [ ] Verify frozen indicator shows in UI
- [ ] Test unfreeze functionality
- [ ] Verify unfreeze works

### Integration Testing
- [ ] Test profit cap with real signal
- [ ] Verify frozen account rejects new trades
- [ ] Verify monitoring continues after breach
- [ ] Verify notifications sent (if enabled)
- [ ] Test with multiple accounts
- [ ] Verify each account tracked independently

---

## 🔧 CONFIGURATION TASKS

### Blue Guardian Accounts
For each Blue Guardian account:
- [ ] Open account in app/web
- [ ] Navigate to Edit → Profit Cap section
- [ ] Enable Profit Cap: ON
- [ ] Cap Type: Dollar
- [ ] Cap Value: 214 (or your specific limit)
- [ ] Buffer: 2% (recommended)
- [ ] Save settings
- [ ] Verify in UI
- [ ] Note in documentation which accounts have cap enabled

### Other Prop Firm Accounts
For each account with profit limits:
- [ ] Identify profit limit from firm rules
- [ ] Open account in app/web
- [ ] Enable profit cap
- [ ] Configure appropriate type/value/buffer
- [ ] Save and verify
- [ ] Document in personal notes

---

## 📊 MONITORING SETUP

### Log Monitoring
- [ ] Set up log aggregation (optional)
- [ ] Create alert for "PROFIT CAP BREACHED" keyword
- [ ] Create dashboard for profit cap status (optional)
- [ ] Document log file locations

### Database Monitoring
- [ ] Verify profit cap columns exist
  ```sql
  SELECT profit_cap_enabled FROM accounts LIMIT 1;
  ```
- [ ] Check which accounts have cap enabled
  ```sql
  SELECT account_key, profit_cap_type, profit_cap_value 
  FROM accounts WHERE profit_cap_enabled = TRUE;
  ```
- [ ] Verify no accounts stuck frozen
  ```sql
  SELECT account_key FROM accounts WHERE profit_cap_frozen = TRUE;
  ```

### Application Monitoring
- [ ] Monitor backend CPU/memory (should be minimal impact)
- [ ] Monitor database query performance
- [ ] Check API response times
- [ ] Verify no error spikes

---

## 📝 DOCUMENTATION TASKS

### Internal Documentation
- [ ] Document which accounts have profit caps enabled
- [ ] Note cap values and buffers for each account
- [ ] Document unfreeze procedures
- [ ] Create runbook for common issues

### Team Communication
- [ ] Notify team of new feature
- [ ] Share deployment schedule
- [ ] Provide access to documentation
- [ ] Schedule training session (if team)

---

## 🎯 SUCCESS CRITERIA

### Must Have (Before Going Live)
- [ ] Backend monitoring loop running
- [ ] No errors in startup logs
- [ ] At least one test account configured
- [ ] Test breach successfully triggered and resolved
- [ ] Unfreeze tested and working

### Should Have (Within 24 Hours)
- [ ] All production accounts configured
- [ ] Monitoring alerts set up
- [ ] Log patterns documented
- [ ] Team trained (if applicable)

### Nice to Have (Within 1 Week)
- [ ] Dashboard showing profit cap status
- [ ] Automated reports on cap proximity
- [ ] Historical breach data analyzed
- [ ] Performance metrics collected

---

## 🆘 ROLLBACK PLAN

### If Critical Issue Found

**Immediate Actions:**
1. Disable profit cap on all accounts via SQL:
   ```sql
   UPDATE accounts SET profit_cap_enabled = FALSE;
   ```

2. Restart backend to clear monitoring loop

3. Investigate issue in logs

4. Fix issue offline

5. Redeploy fixed version

**Rollback Steps (if needed):**
1. SSH into VPS
2. Checkout previous commit: `git checkout <previous-commit-hash>`
3. Restart services
4. Profit cap columns remain in database (harmless if not used)
5. Can forward-deploy fix later

---

## 📞 SUPPORT CONTACTS

### Documentation
- Implementation: `PROFIT_CAP_IMPLEMENTATION.md`
- Bug Check: `PROFIT_CAP_BUG_CHECK_RESULTS.md`
- Deployment: `PROFIT_CAP_DEPLOYMENT_READY.md`
- Web Integration: `WEB_FRONTEND_INTEGRATION.md`
- This Checklist: `PROFIT_CAP_CHECKLIST.md`

### Troubleshooting
See "TROUBLESHOOTING" section in `PROFIT_CAP_DEPLOYMENT_READY.md`

---

## ✅ SIGN-OFF

### Development Team
- [ ] Code reviewed
- [ ] Tests passed
- [ ] Documentation complete
- [ ] Ready for deployment

**Signed:** Kiro AI  
**Date:** July 6, 2026  

### Deployment Team
- [ ] Backend deployed
- [ ] Mobile deployed (if applicable)
- [ ] Web deployed (if applicable)
- [ ] Smoke tests passed

**Signed:** _____________  
**Date:** _____________  

### Quality Assurance
- [ ] Feature tested on test account
- [ ] Breach scenario verified
- [ ] Unfreeze tested
- [ ] Integration verified

**Signed:** _____________  
**Date:** _____________  

### Product Owner
- [ ] Feature meets requirements
- [ ] Prop firm compliance verified
- [ ] Ready for production use
- [ ] Approved for live trading

**Signed:** _____________  
**Date:** _____________  

---

## 🎉 COMPLETION

**All tasks complete?** 

✅ **YES** → Start trading with confidence! Your accounts are protected. 🛡️

⚠️ **NO** → Complete remaining tasks before going live.

---

**Deployment Date:** _____________  
**Go-Live Date:** _____________  
**First Profit Cap Configured:** _____________  
**First Successful Breach Test:** _____________  

---

## 📊 POST-DEPLOYMENT METRICS

Track these for first week:

- Number of accounts with profit cap enabled: _____
- Number of profit cap breaches: _____
- Average time to breach detection: _____s
- Number of false positives: _____
- Number of manual unfreezes: _____
- Average profit at breach: $_____

---

**Checklist Version:** 1.0  
**Last Updated:** July 6, 2026  
**Status:** ✅ Ready for use
