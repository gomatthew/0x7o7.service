# -*- coding: utf-8 -*-
from fastapi import APIRouter

from src.server.dto import ApiCommonResponseDTO
from src.server.service import crm_service


crm_router = APIRouter(prefix="/crm", tags=["CRM 管理"])

crm_router.get("/health", summary="检查 CRM 数据源", response_model=ApiCommonResponseDTO)(crm_service.get_crm_health)
crm_router.get("/dashboard", summary="获取 CRM 综合看板", response_model=ApiCommonResponseDTO)(crm_service.get_dashboard)

crm_router.get("/market/dashboard", summary="获取市场研究统计", response_model=ApiCommonResponseDTO)(crm_service.get_market_dashboard)
crm_router.get("/market/opportunities", summary="获取市场机会列表", response_model=ApiCommonResponseDTO)(crm_service.get_market_opportunities)
crm_router.get("/market/opportunities/{opportunity_id}", summary="获取市场机会详情", response_model=ApiCommonResponseDTO)(crm_service.get_market_opportunity)
crm_router.get("/market/signals", summary="获取市场信号列表", response_model=ApiCommonResponseDTO)(crm_service.get_market_signals)
crm_router.get("/market/signals/{signal_id}", summary="获取市场信号详情", response_model=ApiCommonResponseDTO)(crm_service.get_market_signal)
crm_router.get("/market/agencies", summary="获取代理商候选列表", response_model=ApiCommonResponseDTO)(crm_service.get_market_agencies)
crm_router.get("/market/research_runs", summary="获取市场研究运行记录", response_model=ApiCommonResponseDTO)(crm_service.get_market_research_runs)
crm_router.get("/market/publication", summary="获取最新市场发布记录", response_model=ApiCommonResponseDTO)(crm_service.get_market_publication)

crm_router.get("/companies", summary="获取 CRM 公司列表", response_model=ApiCommonResponseDTO)(crm_service.get_companies)
crm_router.get("/companies/{company_id}", summary="获取 CRM 公司详情", response_model=ApiCommonResponseDTO)(crm_service.get_company)
crm_router.post("/companies", summary="创建 CRM 公司", response_model=ApiCommonResponseDTO)(crm_service.create_company)
crm_router.patch("/companies/{company_id}", summary="更新 CRM 公司", response_model=ApiCommonResponseDTO)(crm_service.update_company)

crm_router.get("/contacts", summary="获取 CRM 联系人列表", response_model=ApiCommonResponseDTO)(crm_service.get_contacts)
crm_router.post("/contacts", summary="创建 CRM 联系人", response_model=ApiCommonResponseDTO)(crm_service.create_contact)
crm_router.patch("/contacts/{contact_id}", summary="更新 CRM 联系人", response_model=ApiCommonResponseDTO)(crm_service.update_contact)

crm_router.get("/deals", summary="获取 CRM Deal 列表", response_model=ApiCommonResponseDTO)(crm_service.get_deals)
crm_router.post("/deals", summary="创建 CRM Deal", response_model=ApiCommonResponseDTO)(crm_service.create_deal)
crm_router.patch("/deals/{deal_id}", summary="更新 CRM Deal", response_model=ApiCommonResponseDTO)(crm_service.update_deal)

crm_router.get("/approvals", summary="获取审批列表", response_model=ApiCommonResponseDTO)(crm_service.get_approvals)
crm_router.post("/approvals", summary="创建审批请求", response_model=ApiCommonResponseDTO)(crm_service.create_approval)
crm_router.post("/approvals/{approval_id}/decision", summary="提交审批决策", response_model=ApiCommonResponseDTO)(crm_service.decide_approval)

crm_router.get("/tasks", summary="获取执行任务列表", response_model=ApiCommonResponseDTO)(crm_service.get_execution_tasks)
crm_router.post("/tasks/{task_id}/transition", summary="变更执行任务状态", response_model=ApiCommonResponseDTO)(crm_service.transition_execution_task)

crm_router.get("/outreach_drafts", summary="获取外联草稿列表", response_model=ApiCommonResponseDTO)(crm_service.get_outreach_drafts)
crm_router.post("/outreach_drafts", summary="创建外联草稿", response_model=ApiCommonResponseDTO)(crm_service.create_outreach_draft)

crm_router.get("/followups", summary="获取跟进任务列表", response_model=ApiCommonResponseDTO)(crm_service.get_followups)
crm_router.post("/followups", summary="创建跟进任务", response_model=ApiCommonResponseDTO)(crm_service.create_followup)
crm_router.patch("/followups/{followup_id}", summary="更新跟进任务", response_model=ApiCommonResponseDTO)(crm_service.update_followup)

crm_router.get("/activities", summary="获取 CRM 活动列表", response_model=ApiCommonResponseDTO)(crm_service.get_activities)
crm_router.post("/activities", summary="创建 CRM 活动", response_model=ApiCommonResponseDTO)(crm_service.create_activity)
