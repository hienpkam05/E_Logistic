// Chọn mục menu đang mở: mục KHỚP CỤ THỂ NHẤT với route hiện tại.
// Cần vì nhiều mục có đường dẫn lồng nhau (/shop ⊂ /shop/shipments ⊂ /shop/shipments/new)
// hoặc cùng đường dẫn khác query ("Quản lý tài khoản" và "Quản lý Shipper" = /staff/accounts?role=SHIPPER).

/**
 * @param items   [{ to }] — `to` là route location của vue-router
 * @param current route hiện tại ({ path, query })
 * @param resolve hàm router.resolve
 * @returns chỉ số mục đang mở, hoặc -1
 */
export function activeIndex(items, current, resolve) {
  let best = -1
  let bestScore = -1
  items.forEach((item, index) => {
    const target = resolve(item.to)
    const path = target.path.replace(/\/+$/, '')
    const here = current.path.replace(/\/+$/, '')
    if (here !== path && !here.startsWith(`${path}/`)) return
    const query = item.to.query ?? {}
    if (!Object.entries(query).every(([k, v]) => current.query?.[k] === v)) return
    const score = path.length * 10 + Object.keys(query).length
    if (score > bestScore) {
      best = index
      bestScore = score
    }
  })
  return best
}
