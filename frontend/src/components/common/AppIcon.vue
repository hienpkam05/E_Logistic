<script setup>
// Icon dùng chung (bộ Lucide). Cấu hình (vd menu trong router/roles.js) chỉ ghi TÊN icon dạng chuỗi.
// Thêm icon: import từ lucide-vue-next rồi khai báo vào ICONS.
import {
  ArrowLeft, Ban, Bell, Box, ChevronLeft, ChevronRight, CircleAlert, CircleCheck, ClipboardList, Clock, Eye,
  House, Inbox, Info, KeyRound, LayoutDashboard, Lock, LockOpen, LogOut, MapPin, Menu, Package, PackagePlus,
  PanelLeftClose, PanelLeftOpen, Pencil, Phone, Plus, RotateCw, Search, Send, ShieldCheck, SlidersHorizontal,
  Truck, Undo2, User, UserPlus, Users, Wallet, Warehouse, X,
} from 'lucide-vue-next'
import { computed } from 'vue'

const ICONS = {
  'arrow-left': ArrowLeft, ban: Ban, bell: Bell, box: Box, 'chevron-left': ChevronLeft, 'chevron-right': ChevronRight,
  alert: CircleAlert, check: CircleCheck, clipboard: ClipboardList, clock: Clock, eye: Eye, home: House,
  inbox: Inbox, info: Info, key: KeyRound, dashboard: LayoutDashboard, lock: Lock, unlock: LockOpen,
  logout: LogOut, 'map-pin': MapPin, menu: Menu, package: Package, 'package-plus': PackagePlus,
  'panel-close': PanelLeftClose, 'panel-open': PanelLeftOpen, pencil: Pencil, phone: Phone, plus: Plus,
  reload: RotateCw, search: Search, send: Send, shield: ShieldCheck, filter: SlidersHorizontal, truck: Truck,
  undo: Undo2, user: User, 'user-plus': UserPlus, users: Users, wallet: Wallet, warehouse: Warehouse, close: X,
}

const props = defineProps({
  name: { type: String, required: true },
  size: { type: Number, default: 18 },
})

const component = computed(() => ICONS[props.name] ?? Box)
</script>

<template>
  <component :is="component" class="icon" :size="size" :stroke-width="2" aria-hidden="true" />
</template>
