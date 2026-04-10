from django.db.models import Q, F
from django.utils import timezone
from datetime import timedelta


def calculate_metrics(properties_qs, selected_metrics):
    results = {}

    if not properties_qs.exists():
        return results

    # -------------------------
    # Inventory (Active listings)
    # -------------------------
    if 'inventory' in selected_metrics:
        results['inventory'] = properties_qs.filter(
            Q(status='Active') | Q(status='Coming Soon')
        ).count()

    # -------------------------
    # Avg DOM & Median DOM
    # -------------------------
    if 'avg_dom' in selected_metrics or 'median_dom' in selected_metrics:
        closed = properties_qs.filter(
            status='Closed',
            listing_date__isnull=False,
            close_date__isnull=False,
        ).values('listing_date', 'close_date')

        dom_list = []
        for p in closed:
            if p['listing_date'] and p['close_date']:
                delta = p['close_date'] - p['listing_date']
                if delta.days > 0:   # exclude same-day closings (data errors)
                    dom_list.append(delta.days)

        if 'avg_dom' in selected_metrics:
            results['avg_dom'] = round(sum(dom_list) / len(dom_list), 1) if dom_list else None

        if 'median_dom' in selected_metrics:
            results['median_dom'] = _median(dom_list) if dom_list else None

    # -------------------------
    # Price Per Sq. Ft. (median)
    # -------------------------
    if 'price_per_sqft' in selected_metrics:
        values = list(
            properties_qs
            .filter(price_per_sqft__isnull=False, price_per_sqft__gt=0)
            .values_list('price_per_sqft', flat=True)
            .order_by('price_per_sqft')
        )
        results['price_per_sqft'] = _median(values)

    # -------------------------
    # Price Decreased %
    # Closed where sold_price < list_price
    # -------------------------
    if 'price_decreased_pct' in selected_metrics:
        closed = properties_qs.filter(
            status='Closed',
            sold_price__isnull=False,
            sold_price__gt=0,
            list_price__isnull=False,
            list_price__gt=0,
        )
        total_closed = closed.count()
        decreased = closed.filter(sold_price__lt=F('list_price')).count()
        results['price_decreased_pct'] = round((decreased / total_closed) * 100, 2) if total_closed else None

    # -------------------------
    # Price Increased %
    # Closed where sold_price > list_price
    # -------------------------
    if 'price_increased_pct' in selected_metrics:
        closed = properties_qs.filter(
            status='Closed',
            sold_price__isnull=False,
            sold_price__gt=0,
            list_price__isnull=False,
            list_price__gt=0,
        )
        total_closed = closed.count()
        increased = closed.filter(sold_price__gt=F('list_price')).count()
        results['price_increased_pct'] = round((increased / total_closed) * 100, 2) if total_closed else None

    # -------------------------
    # Median List Price
    # -------------------------
    if 'median_list_price' in selected_metrics:
        prices = list(
            properties_qs
            .filter(list_price__isnull=False, list_price__gt=0)
            .values_list('list_price', flat=True)
            .order_by('list_price')
        )
        results['median_list_price'] = _median(prices)

    # -------------------------
    # Median Price of New Listings (last 30 days)
    # -------------------------
    if 'median_price_new_listings' in selected_metrics:
        thirty_days_ago = timezone.now() - timedelta(days=30)
        prices = list(
            properties_qs
            .filter(
                listing_date__gte=thirty_days_ago,
                list_price__isnull=False,
                list_price__gt=0,
            )
            .values_list('list_price', flat=True)
            .order_by('list_price')
        )
        results['median_price_new_listings'] = _median(prices)

    return results


def _median(values):
    if not values:
        return None
    sorted_vals = sorted([float(v) for v in values])
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 0:
        return round((sorted_vals[mid - 1] + sorted_vals[mid]) / 2, 2)
    return round(sorted_vals[mid], 2)