# Custom IERS A URLs from config file example

# Disclaimer: The "mirror" URLs here are not real mirrors. Do not use them for production.

# And to test this properly, clear your cache if you want. Cache is in ~/.astropy/cache by default.

# In your ~/.astropy/config/astropy.cfg (or wherever you have configured astropy to store it), add this:

# [utils.iers.iers]
# iers_auto_url = https://astroconda.org/aux/astropy_mirror/iers_a_1/finals2000A.all
# iers_auto_url_mirror = https://astroconda.org/aux/astropy_mirror/iers_a_2/finals2000A.all
