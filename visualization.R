# ============================================================
# Warehouse Change Analysis using Landsat 30m Data
# ============================================================

# ------------------------------------------------------------
# 0. Set working directory and load packages
# ------------------------------------------------------------
setwd("E:/julie")

library(terra)
library(sf)
library(ggplot2)
library(dplyr)
library(tidyr)

# ------------------------------------------------------------
# 1. Read Landsat 30m warehouse rasters
# ------------------------------------------------------------
warehouse_2010 <- rast("warehouse_2010_landsat30m.tif")
warehouse_2015 <- rast("warehouse_2015_landsat30m.tif")
warehouse_2020 <- rast("warehouse_2020_landsat30m.tif")
warehouse_2025 <- rast("warehouse_2025_landsat30m.tif")

indi_boundary <- st_read("IndiPolygon.shp", quiet = TRUE)
city_center   <- st_read("IndiCenter.shp", quiet = TRUE)

# ------------------------------------------------------------
# 2. Match CRS
# ------------------------------------------------------------
target_crs <- crs(warehouse_2010)

indi_boundary <- st_transform(indi_boundary, crs = target_crs)
city_center   <- st_transform(city_center, crs = target_crs)

indi_boundary_v <- vect(indi_boundary)
city_center_v   <- vect(city_center)

# ------------------------------------------------------------
# 3. Convert all warehouse rasters to binary 0/1
# ------------------------------------------------------------
make_binary <- function(r) {
  r[is.na(r)] <- 0
  r <- ifel(r > 0, 1, 0)
  return(r)
}

warehouse_2010 <- make_binary(warehouse_2010)
warehouse_2015 <- make_binary(warehouse_2015)
warehouse_2020 <- make_binary(warehouse_2020)
warehouse_2025 <- make_binary(warehouse_2025)

# ------------------------------------------------------------
# 4. Align all rasters to 2010 grid
# ------------------------------------------------------------
warehouse_2010_30 <- warehouse_2010
warehouse_2015_30 <- resample(warehouse_2015, warehouse_2010_30, method = "near")
warehouse_2020_30 <- resample(warehouse_2020, warehouse_2010_30, method = "near")
warehouse_2025_30 <- resample(warehouse_2025, warehouse_2010_30, method = "near")

# ------------------------------------------------------------
# 5. Plot yearly warehouse maps in RStudio
# ------------------------------------------------------------
par(mfrow = c(2, 2), mar = c(3, 3, 3, 5))

plot(warehouse_2010_30, main = "Warehouse 2010 Landsat 30m", col = c("white", "blue"))
lines(indi_boundary_v, col = "black", lwd = 2)

plot(warehouse_2015_30, main = "Warehouse 2015 Landsat 30m", col = c("white", "blue"))
lines(indi_boundary_v, col = "black", lwd = 2)

plot(warehouse_2020_30, main = "Warehouse 2020 Landsat 30m", col = c("white", "blue"))
lines(indi_boundary_v, col = "black", lwd = 2)

plot(warehouse_2025_30, main = "Warehouse 2025 Landsat 30m", col = c("white", "blue"))
lines(indi_boundary_v, col = "black", lwd = 2)

# ------------------------------------------------------------
# 6. Save yearly warehouse maps as PDF
# ------------------------------------------------------------
pdf("warehouse_year_maps_landsat30m.pdf", width = 10, height = 8)

par(mfrow = c(2, 2), mar = c(3, 3, 3, 5))

plot(warehouse_2010_30, main = "Warehouse 2010 Landsat 30m", col = c("white", "blue"))
lines(indi_boundary_v, col = "black", lwd = 2)

plot(warehouse_2015_30, main = "Warehouse 2015 Landsat 30m", col = c("white", "blue"))
lines(indi_boundary_v, col = "black", lwd = 2)

plot(warehouse_2020_30, main = "Warehouse 2020 Landsat 30m", col = c("white", "blue"))
lines(indi_boundary_v, col = "black", lwd = 2)

plot(warehouse_2025_30, main = "Warehouse 2025 Landsat 30m", col = c("white", "blue"))
lines(indi_boundary_v, col = "black", lwd = 2)

dev.off()

# ------------------------------------------------------------
# 7. Create change rasters
# ------------------------------------------------------------
growth_2010_2015 <- ifel(warehouse_2010_30 == 0 & warehouse_2015_30 == 1, 1, 0)
growth_2015_2020 <- ifel(warehouse_2015_30 == 0 & warehouse_2020_30 == 1, 1, 0)
growth_2020_2025 <- ifel(warehouse_2020_30 == 0 & warehouse_2025_30 == 1, 1, 0)

lost_2010_2015 <- ifel(warehouse_2010_30 == 1 & warehouse_2015_30 == 0, 1, 0)
lost_2015_2020 <- ifel(warehouse_2015_30 == 1 & warehouse_2020_30 == 0, 1, 0)
lost_2020_2025 <- ifel(warehouse_2020_30 == 1 & warehouse_2025_30 == 0, 1, 0)

persistent_2010_2015 <- ifel(warehouse_2010_30 == 1 & warehouse_2015_30 == 1, 1, 0)
persistent_2015_2020 <- ifel(warehouse_2015_30 == 1 & warehouse_2020_30 == 1, 1, 0)
persistent_2020_2025 <- ifel(warehouse_2020_30 == 1 & warehouse_2025_30 == 1, 1, 0)

# ------------------------------------------------------------
# 8. Save change rasters
# ------------------------------------------------------------
writeRaster(growth_2010_2015, "New_warehouse_2010_2015_landsat30m.tif", overwrite = TRUE)
writeRaster(growth_2015_2020, "New_warehouse_2015_2020_landsat30m.tif", overwrite = TRUE)
writeRaster(growth_2020_2025, "New_warehouse_2020_2025_landsat30m.tif", overwrite = TRUE)

writeRaster(lost_2010_2015, "Lost_warehouse_2010_2015_landsat30m.tif", overwrite = TRUE)
writeRaster(lost_2015_2020, "Lost_warehouse_2015_2020_landsat30m.tif", overwrite = TRUE)
writeRaster(lost_2020_2025, "Lost_warehouse_2020_2025_landsat30m.tif", overwrite = TRUE)

writeRaster(persistent_2010_2015, "Persistent_warehouse_2010_2015_landsat30m.tif", overwrite = TRUE)
writeRaster(persistent_2015_2020, "Persistent_warehouse_2015_2020_landsat30m.tif", overwrite = TRUE)
writeRaster(persistent_2020_2025, "Persistent_warehouse_2020_2025_landsat30m.tif", overwrite = TRUE)

# ------------------------------------------------------------
# 9. Plot new warehouse change maps in RStudio
# ------------------------------------------------------------
par(mfrow = c(1, 3), mar = c(3, 3, 3, 5))

plot(growth_2010_2015, main = "New Warehouse 2010-2015", col = c("lightgrey", "red"))
lines(indi_boundary_v, col = "black", lwd = 2)
points(city_center_v, pch = 8, col = "black", cex = 1.2)

plot(growth_2015_2020, main = "New Warehouse 2015-2020", col = c("lightgrey", "red"))
lines(indi_boundary_v, col = "black", lwd = 2)
points(city_center_v, pch = 8, col = "black", cex = 1.2)

plot(growth_2020_2025, main = "New Warehouse 2020-2025", col = c("lightgrey", "red"))
lines(indi_boundary_v, col = "black", lwd = 2)
points(city_center_v, pch = 8, col = "black", cex = 1.2)

# ------------------------------------------------------------
# 10. Save change maps as PDF
# ------------------------------------------------------------
pdf("warehouse_change_maps_landsat30m.pdf", width = 12, height = 5)

par(mfrow = c(1, 3), mar = c(3, 3, 3, 5))

plot(growth_2010_2015, main = "New Warehouse 2010-2015", col = c("lightgrey", "red"))
lines(indi_boundary_v, col = "black", lwd = 2)
points(city_center_v, pch = 8, col = "black", cex = 1.2)

plot(growth_2015_2020, main = "New Warehouse 2015-2020", col = c("lightgrey", "red"))
lines(indi_boundary_v, col = "black", lwd = 2)
points(city_center_v, pch = 8, col = "black", cex = 1.2)

plot(growth_2020_2025, main = "New Warehouse 2020-2025", col = c("lightgrey", "red"))
lines(indi_boundary_v, col = "black", lwd = 2)
points(city_center_v, pch = 8, col = "black", cex = 1.2)

dev.off()

# ------------------------------------------------------------
# 11. Area calculation
# ------------------------------------------------------------
pixel_area_sqkm <- prod(res(warehouse_2010_30)) / 1000000

count_pixels <- function(r) {
  val <- global(r, fun = "sum", na.rm = TRUE)[1, 1]
  if (is.na(val)) val <- 0
  return(val)
}

area_sqkm <- function(r) {
  count_pixels(r) * pixel_area_sqkm
}

year_area_table <- data.frame(
  Year = c(2010, 2015, 2020, 2025),
  Warehouse_Pixels = c(
    count_pixels(warehouse_2010_30),
    count_pixels(warehouse_2015_30),
    count_pixels(warehouse_2020_30),
    count_pixels(warehouse_2025_30)
  ),
  Warehouse_sqkm = c(
    area_sqkm(warehouse_2010_30),
    area_sqkm(warehouse_2015_30),
    area_sqkm(warehouse_2020_30),
    area_sqkm(warehouse_2025_30)
  )
)

summary_table <- data.frame(
  Period = c("2010-2015", "2015-2020", "2020-2025"),
  New_Pixels = c(
    count_pixels(growth_2010_2015),
    count_pixels(growth_2015_2020),
    count_pixels(growth_2020_2025)
  ),
  Lost_Pixels = c(
    count_pixels(lost_2010_2015),
    count_pixels(lost_2015_2020),
    count_pixels(lost_2020_2025)
  ),
  Persistent_Pixels = c(
    count_pixels(persistent_2010_2015),
    count_pixels(persistent_2015_2020),
    count_pixels(persistent_2020_2025)
  ),
  New_sqkm = c(
    area_sqkm(growth_2010_2015),
    area_sqkm(growth_2015_2020),
    area_sqkm(growth_2020_2025)
  ),
  Lost_sqkm = c(
    area_sqkm(lost_2010_2015),
    area_sqkm(lost_2015_2020),
    area_sqkm(lost_2020_2025)
  ),
  Persistent_sqkm = c(
    area_sqkm(persistent_2010_2015),
    area_sqkm(persistent_2015_2020),
    area_sqkm(persistent_2020_2025)
  )
)

print(year_area_table)
print(summary_table)

write.csv(year_area_table, "warehouse_area_by_year_landsat30m.csv", row.names = FALSE)
write.csv(summary_table, "warehouse_change_summary_landsat30m.csv", row.names = FALSE)

# ------------------------------------------------------------
# 12. Bar chart: warehouse area by year
# ------------------------------------------------------------
p1 <- ggplot(year_area_table, aes(x = factor(Year), y = Warehouse_sqkm)) +
  geom_col(fill = "steelblue") +
  theme_minimal() +
  labs(
    title = "Warehouse Area by Year",
    x = "Year",
    y = "Warehouse Area (sq km)"
  )

print(p1)

ggsave("warehouse_area_by_year_landsat30m.png", p1, width = 8, height = 5, dpi = 300)

# ------------------------------------------------------------
# 13. Bar chart: new, lost, persistent warehouse area
# ------------------------------------------------------------
change_long <- summary_table %>%
  select(Period, New_sqkm, Lost_sqkm, Persistent_sqkm) %>%
  pivot_longer(
    cols = c(New_sqkm, Lost_sqkm, Persistent_sqkm),
    names_to = "Change_Type",
    values_to = "Area_sqkm"
  )

p2 <- ggplot(change_long, aes(x = Period, y = Area_sqkm, fill = Change_Type)) +
  geom_col(position = "dodge") +
  theme_minimal() +
  labs(
    title = "Warehouse Change by Period",
    x = "Period",
    y = "Area (sq km)",
    fill = "Change Type"
  )

print(p2)

ggsave("warehouse_change_by_period_landsat30m.png", p2, width = 8, height = 5, dpi = 300)

# ------------------------------------------------------------
# 14. Direction and distance analysis
# ------------------------------------------------------------
get_change_points <- function(change_raster) {
  expansion_pixels <- ifel(change_raster == 1, 1, NA)
  change_points <- as.points(expansion_pixels, na.rm = TRUE)
  return(change_points)
}

make_expansion_df <- function(change_raster, city_center, period_name) {
  
  change_points <- get_change_points(change_raster)
  
  if (is.null(change_points) || nrow(change_points) == 0) {
    return(NULL)
  }
  
  coords <- crds(change_points)
  center_xy <- st_coordinates(city_center)[1, ]
  
  angles <- atan2(coords[, 2] - center_xy[2], coords[, 1] - center_xy[1])
  angles_deg <- (angles * 180 / pi) %% 360
  bearing <- (450 - angles_deg) %% 360
  
  expansion_sf <- st_as_sf(
    data.frame(x = coords[, 1], y = coords[, 2]),
    coords = c("x", "y"),
    crs = st_crs(city_center)
  )
  
  distances_m <- st_distance(expansion_sf, city_center)
  
  df <- data.frame(
    Period = period_name,
    x = coords[, 1],
    y = coords[, 2],
    Bearing = bearing,
    Distance_km = as.numeric(distances_m) / 1000
  )
  
  return(df)
}

expansion_all <- bind_rows(
  make_expansion_df(growth_2010_2015, city_center, "2010-2015"),
  make_expansion_df(growth_2015_2020, city_center, "2015-2020"),
  make_expansion_df(growth_2020_2025, city_center, "2020-2025")
)

write.csv(expansion_all, "warehouse_expansion_points_landsat30m.csv", row.names = FALSE)

# ------------------------------------------------------------
# 15. Direction chart
# ------------------------------------------------------------
rose_data <- expansion_all %>%
  mutate(
    Direction_Bin = cut(
      Bearing,
      breaks = seq(0, 360, by = 30),
      include.lowest = TRUE,
      right = FALSE
    )
  ) %>%
  group_by(Period, Direction_Bin) %>%
  summarise(Count = n(), .groups = "drop")

p3 <- ggplot(rose_data, aes(x = Direction_Bin, y = Count, fill = Period)) +
  geom_col(position = "dodge") +
  coord_polar() +
  theme_minimal() +
  labs(
    title = "Direction of New Warehouse Expansion",
    x = NULL,
    y = "Pixel Count"
  )

print(p3)

ggsave("warehouse_expansion_direction_landsat30m.png", p3, width = 8, height = 6, dpi = 300)

# ------------------------------------------------------------
# 16. Distance histogram
# ------------------------------------------------------------
p4 <- ggplot(expansion_all, aes(x = Distance_km, fill = Period)) +
  geom_histogram(binwidth = 2, alpha = 0.6, position = "identity") +
  theme_minimal() +
  labs(
    title = "Distance of New Warehouse from City Center",
    x = "Distance (km)",
    y = "Pixel Count"
  )

print(p4)

ggsave("warehouse_expansion_distance_landsat30m.png", p4, width = 8, height = 5, dpi = 300)

# ------------------------------------------------------------
# 17. Finish
# ------------------------------------------------------------
cat("Done. Maps, charts, rasters, and CSV tables have been saved in E:/julie.\n")
