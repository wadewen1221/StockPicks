<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup>
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  min-height: 100vh;
  color: #ffffff;
}

#app {
  min-height: 100vh;
}

/* Element Plus 暗色背景适配 */
.el-tabs__item {
  color: #aaaaaa !important;
  font-size: 15px;
}

.el-tabs__item.is-active {
  color: #00d4ff !important;
}

.el-tabs__item:hover {
  color: #ffffff !important;
}

.el-tabs__active-bar {
  background-color: #00d4ff !important;
}

.el-tabs__nav-wrap::after {
  background-color: rgba(255, 255, 255, 0.15) !important;
}

.el-page-header__title {
  color: #ffffff !important;
  font-weight: 600;
}

.el-page-header__content {
  color: #e0e0e0 !important;
}

.el-button {
  color: #ffffff !important;
}

.el-button--primary {
  background-color: #00d4ff !important;
  border-color: #00d4ff !important;
  color: #1a1a2e !important;
}

.el-button--primary:hover {
  background-color: #33ddff !important;
  border-color: #33ddff !important;
}

.el-button--default {
  background-color: rgba(255, 255, 255, 0.08) !important;
  border-color: rgba(255, 255, 255, 0.15) !important;
  color: #e0e0e0 !important;
}

.el-button--default:hover {
  background-color: rgba(255, 255, 255, 0.15) !important;
  border-color: rgba(255, 255, 255, 0.25) !important;
  color: #ffffff !important;
}

.el-tag {
  color: #ffffff !important;
}

.el-dialog__title {
  color: #ffffff !important;
}

.el-form-item__label {
  color: #d0d0d0 !important;
}

.el-input__wrapper {
  background-color: rgba(255, 255, 255, 0.08) !important;
  box-shadow: none !important;
}

.el-input__inner {
  color: #ffffff !important;
}

.el-input__inner::placeholder {
  color: #888888 !important;
}

.el-select__wrapper {
  background-color: rgba(255, 255, 255, 0.08) !important;
  box-shadow: none !important;
}

.el-select__selected-item {
  color: #ffffff !important;
}

.el-select__placeholder {
  color: #888888 !important;
}

.el-card {
  --el-card-bg-color: rgba(255, 255, 255, 0.06);
  --el-card-border-color: rgba(255, 255, 255, 0.1);
  background-color: rgba(255, 255, 255, 0.06) !important;
  border-color: rgba(255, 255, 255, 0.1) !important;
}

.el-card__header {
  border-color: rgba(255, 255, 255, 0.1) !important;
  color: #ffffff !important;
}

.el-card__body {
  color: #e0e0e0 !important;
}

.el-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255, 255, 255, 0.08);
  --el-table-text-color: #e0e0e0;
  --el-table-header-text-color: #ffffff;
  --el-table-border-color: rgba(255, 255, 255, 0.08);
  background-color: transparent !important;
}

.el-table th.el-table__cell {
  background-color: rgba(255, 255, 255, 0.08) !important;
  color: #ffffff !important;
  font-weight: 600;
}

.el-table td.el-table__cell {
  color: #e0e0e0 !important;
}

.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell {
  background-color: rgba(255, 255, 255, 0.03) !important;
}

.el-descriptions__label {
  color: #d0d0d0 !important;
}

.el-descriptions__content {
  color: #e0e0e0 !important;
}

.el-empty__description {
  color: #888888 !important;
}

.el-loading-mask {
  background-color: rgba(26, 26, 46, 0.8) !important;
}

.el-loading-spinner .circular {
  stroke: #00d4ff !important;
}

.el-tabs--border-card {
  --el-tabs-border-card-bg-color: transparent;
  background-color: transparent !important;
  border: none !important;
}

.el-tabs--border-card > .el-tabs__header {
  background-color: rgba(255, 255, 255, 0.04) !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
}

.el-tabs--border-card > .el-tabs__header .el-tabs__item {
  color: #aaaaaa !important;
  border: none !important;
}

.el-tabs--border-card > .el-tabs__header .el-tabs__item.is-active {
  color: #00d4ff !important;
  background-color: rgba(255, 255, 255, 0.06) !important;
}

.el-tabs--border-card > .el-tabs__header .el-tabs__item:hover {
  color: #ffffff !important;
}
</style>
