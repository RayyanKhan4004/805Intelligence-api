from django.db.models import Avg, F, Q


def calculate_metrics(properties_qs, selected_metrics):
    results = {}

    if not properties_qs.exists():
        return results

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
    # Median Sale Price
    # -------------------------
    if 'median_sale_price' in selected_metrics:
        prices = list(
            properties_qs
            .filter(sold_price__isnull=False, sold_price__gt=0)
            .values_list('sold_price', flat=True)
            .order_by('sold_price')
        )
        results['median_sale_price'] = _median(prices)

    # -------------------------
    # Price Per Sqft (median, not avg — more accurate)
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
    # Days on Market
    # -------------------------
    if 'days_on_market' in selected_metrics:
        closed = properties_qs.filter(
            status='Closed',
            listing_date__isnull=False,
            close_date__isnull=False,
        ).values('listing_date', 'close_date')

        dom_list = []
        for p in closed:
            if p['listing_date'] and p['close_date']:
                delta = p['close_date'] - p['listing_date']
                if delta.days >= 0:
                    dom_list.append(delta.days)

        results['days_on_market'] = round(sum(dom_list) / len(dom_list), 1) if dom_list else None

    # -------------------------
    # Inventory (Active listings)
    # -------------------------
    if 'inventory' in selected_metrics:
        results['inventory'] = properties_qs.filter(
            Q(status='Active') | Q(status='Coming Soon')
        ).count()

    # -------------------------
    # List-to-Sale Price Ratio
    # -------------------------
    if 'list_to_sale_ratio' in selected_metrics:
        ratios = []
        rows = properties_qs.filter(
            sold_price__isnull=False,
            sold_price__gt=0,
            list_price__isnull=False,
            list_price__gt=0,
            status='Closed',
        ).values('sold_price', 'list_price')

        for p in rows:
            ratios.append(float(p['sold_price']) / float(p['list_price']))

        results['list_to_sale_ratio'] = round(sum(ratios) / len(ratios), 4) if ratios else None

    # -------------------------
    # Price Reductions %
    # Properties where list_price was reduced before closing
    # We detect this as: sold_price < list_price (meaning they dropped the price)
    # -------------------------
    if 'price_reductions' in selected_metrics:
        closed = properties_qs.filter(
            status='Closed',
            sold_price__isnull=False,
            sold_price__gt=0,
            list_price__isnull=False,
            list_price__gt=0,
        )
        total_closed = closed.count()
        reduced = closed.filter(sold_price__lt=F('list_price')).count()
        results['price_reductions_pct'] = round((reduced / total_closed) * 100, 2) if total_closed else None

    # -------------------------
    # New Listings vs Closed Sales
    # -------------------------
    if 'new_vs_closed' in selected_metrics:
        results['new_listings'] = properties_qs.filter(
            listing_date__isnull=False
        ).count()
        results['closed_sales'] = properties_qs.filter(
            status='Closed'
        ).count()

    return results


def _median(values):
    if not values:
        return None
    n = len(values)
    mid = n // 2
    if n % 2 == 0:
        return round((float(values[mid - 1]) + float(values[mid])) / 2, 2)
    return round(float(values[mid]), 2)