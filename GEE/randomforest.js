/***************************************************************
 * Multi-Year Warehouse Detection with Random Forest
 * All years use Landsat 30 m
 *
 * Objects:
 * 1 = Warehouse_2010
 * 2 = Warehouse_2015
 * 3 = Warehouse_2020
 * 4 = Warehouse_2025
 * 5 = Vegetation_2025
 * 6 = Water_2025
 * 7 = Road_2025
 * 8 = Urban_2025
 * 9 = airport_2025
 ***************************************************************/


// =============================================================
// Step 1: Define fixed AOI manually from coordinates
// =============================================================

var ROIA = ee.Geometry.Polygon([
  [[-85.78310468198428, 39.97099990979417],
   [-85.70705869199405, 39.97099990979417],
   [-85.70705869199405, 40.05080779450227],
   [-85.78310468198428, 40.05080779450227],
   [-85.78310468198428, 39.97099990979417]]
]);

var ROIG1 = ee.Geometry.Polygon([
  [[-86.10905708976979, 39.5315811776021],
   [-86.0273462743401, 39.5315811776021],
   [-86.0273462743401, 39.640326958679935],
   [-86.10905708976979, 39.640326958679935],
   [-86.10905708976979, 39.5315811776021]]
]);

var ROIG2 = ee.Geometry.Polygon([
  [[-86.09510077747704, 39.46237512039642],
   [-85.98695410999657, 39.46237512039642],
   [-85.98695410999657, 39.52874087990522],
   [-86.09510077747704, 39.52874087990522],
   [-86.09510077747704, 39.46237512039642]]
]);

var aoi = ee.Geometry.Polygon([
  [[-86.4325, 39.65593],
   [-86.23163, 39.65593],
   [-86.23163, 39.77556],
   [-86.41325, 39.77556],
   [-86.41325, 39.65593]]
]);

var aoi2 = ee.Geometry.Polygon([
  [[-86.52219315282441, 39.593025996959604],
   [-86.4552452158127, 39.593025996959604],
   [-86.4552452158127, 39.6301868954912],
   [-86.52219315282441, 39.6301868954912],
   [-86.52219315282441, 39.593025996959604]]
]);

var aoi3 = ee.Geometry.Polygon([
  [[-86.51699551415884, 40.01872949729343],
   [-86.43013485742055, 40.01872949729343],
   [-86.43013485742055, 40.08311652940348],
   [-86.51699551415884, 40.08311652940348],
   [-86.51699551415884, 40.01872949729343]]
]);

var aoi4 = ee.Geometry.Polygon([
  [[-86.42000149776945, 39.941952066033394],
   [-86.33608271867449, 39.941952066033394],
   [-86.33608271867449, 39.98933526737124],
   [-86.42000149776945, 39.98933526737124],
   [-86.42000149776945, 39.941952066033394]]
]);

var aoi5 = ee.Geometry.Polygon([
  [[-86.28427659318373, 39.853404916355146],
   [-86.19458352372573, 39.853404916355146],
   [-86.19458352372573, 39.95045961723545],
   [-86.28427659318373, 39.95045961723545],
   [-86.28427659318373, 39.853404916355146]]
]);

var aoi6 = ee.Geometry.Polygon([
  [[-86.103553826318, 39.784943054081694],
   [-85.98304753969691, 39.784943054081694],
   [-85.98304753969691, 39.84032440656338],
   [-86.103553826318, 39.84032440656338],
   [-86.103553826318, 39.784943054081694]]
]);

var aoi7 = ee.Geometry.Polygon([
  [[-85.95517501165573, 39.7974392027313],
   [-85.86900100042526, 39.7974392027313],
   [-85.86900100042526, 39.86994017714407],
   [-85.95517501165573, 39.86994017714407],
   [-85.95517501165573, 39.7974392027313]]
]);

var combinedAOI = ee.FeatureCollection([
  ee.Feature(aoi),
  ee.Feature(aoi2),
  ee.Feature(aoi3),
  ee.Feature(aoi4),
  ee.Feature(aoi5),
  ee.Feature(aoi6),
  ee.Feature(aoi7),
  ee.Feature(ROIA),
  ee.Feature(ROIG1),
  ee.Feature(ROIG2)
]).geometry();

Map.centerObject(combinedAOI, 10);
Map.setOptions('SATELLITE');
Map.addLayer(combinedAOI, {color: 'yellow'}, 'Combined AOI', false);
print('Combined AOI area sq km:', combinedAOI.area().divide(1e6));


// =============================================================
// Step 2: Training samples
// =============================================================

var warehouse2010 = Warehouse_2010.map(function(f) {
  return f.set('class', 1);
});

var warehouse2015 = Warehouse_2015.map(function(f) {
  return f.set('class', 1);
});

var warehouse2020 = Warehouse_2020.map(function(f) {
  return f.set('class', 1);
});

var warehouse2025 = Warehouse_2025.map(function(f) {
  return f.set('class', 1);
});

var nonwarehouse2025 = Vegetation_2025
  .merge(Water_2025)
  .merge(Road_2025)
  .merge(Urban_2025)
  .merge(airport_2025)
  .map(function(f) {
    return f.set('class', 0);
  });

var training2010 = warehouse2010.merge(nonwarehouse2025);
var training2015 = warehouse2015.merge(nonwarehouse2025);
var training2020 = warehouse2020.merge(nonwarehouse2025);
var training2025 = warehouse2025.merge(nonwarehouse2025);

Map.addLayer(warehouse2010, {color: 'cyan'}, 'Warehouse 2010 Training', false);
Map.addLayer(warehouse2015, {color: 'red'}, 'Warehouse 2015 Training', false);
Map.addLayer(warehouse2020, {color: 'lime'}, 'Warehouse 2020 Training', false);
Map.addLayer(warehouse2025, {color: 'blue'}, 'Warehouse 2025 Training', false);
Map.addLayer(nonwarehouse2025, {color: 'orange'}, 'Non-Warehouse Training', false);


// =============================================================
// Step 3: Landsat preprocessing
// =============================================================

function maskL57(image) {
  var qa = image.select('QA_PIXEL');

  var mask = qa.bitwiseAnd(1 << 3).eq(0)
    .and(qa.bitwiseAnd(1 << 4).eq(0))
    .and(qa.bitwiseAnd(1 << 5).eq(0));

  var sr = image.select(
      ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7']
    )
    .multiply(0.0000275)
    .add(-0.2)
    .rename(['BLUE', 'GREEN', 'RED', 'NIR', 'SWIR1', 'SWIR2']);

  return sr.updateMask(mask)
    .copyProperties(image, image.propertyNames());
}

function maskL89(image) {
  var qa = image.select('QA_PIXEL');

  var mask = qa.bitwiseAnd(1 << 3).eq(0)
    .and(qa.bitwiseAnd(1 << 4).eq(0))
    .and(qa.bitwiseAnd(1 << 5).eq(0));

  var sr = image.select(
      ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7']
    )
    .multiply(0.0000275)
    .add(-0.2)
    .rename(['BLUE', 'GREEN', 'RED', 'NIR', 'SWIR1', 'SWIR2']);

  return sr.updateMask(mask)
    .copyProperties(image, image.propertyNames());
}


// =============================================================
// Step 4: Build yearly Landsat composites
// =============================================================

function getComposite2010() {
  var start = ee.Date('2010-05-01');
  var end = ee.Date('2010-10-01');

  var l5 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
    .filterBounds(combinedAOI)
    .filterDate(start, end)
    .map(maskL57);

  var l7 = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
    .filterBounds(combinedAOI)
    .filterDate(start, end)
    .map(maskL57);

  return l5.merge(l7).median().clip(combinedAOI);
}

function getComposite2015() {
  var start = ee.Date('2015-05-01');
  var end = ee.Date('2015-10-01');

  var l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
    .filterBounds(combinedAOI)
    .filterDate(start, end)
    .map(maskL89);

  return l8.median().clip(combinedAOI);
}

function getComposite2020() {
  var start = ee.Date('2020-05-01');
  var end = ee.Date('2020-10-01');

  var l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
    .filterBounds(combinedAOI)
    .filterDate(start, end)
    .map(maskL89);

  return l8.median().clip(combinedAOI);
}

function getComposite2025() {
  var start = ee.Date('2025-05-01');
  var end = ee.Date('2025-10-01');

  var l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
    .filterBounds(combinedAOI)
    .filterDate(start, end)
    .map(maskL89);

  var l9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
    .filterBounds(combinedAOI)
    .filterDate(start, end)
    .map(maskL89);

  return l8.merge(l9).median().clip(combinedAOI);
}

function getYearComposite(year) {
  year = ee.Number(year);

  return ee.Image(
    ee.Algorithms.If(
      year.eq(2010), getComposite2010(),
      ee.Algorithms.If(
        year.eq(2015), getComposite2015(),
        ee.Algorithms.If(
          year.eq(2020), getComposite2020(),
          getComposite2025()
        )
      )
    )
  );
}


// =============================================================
// Step 5: Add spectral indices
// =============================================================

function addIndices(image) {
  var ndvi = image.normalizedDifference(['NIR', 'RED']).rename('NDVI');
  var ndbi = image.normalizedDifference(['SWIR1', 'NIR']).rename('NDBI');
  var mndwi = image.normalizedDifference(['GREEN', 'SWIR1']).rename('MNDWI');

  var bsi = image.expression(
    '((SWIR1 + RED) - (NIR + BLUE)) / ((SWIR1 + RED) + (NIR + BLUE) + 1e-10)',
    {
      SWIR1: image.select('SWIR1'),
      RED: image.select('RED'),
      NIR: image.select('NIR'),
      BLUE: image.select('BLUE')
    }
  ).rename('BSI');

  var ui = image.expression(
    '(SWIR1 - NIR) / (SWIR1 + NIR + 1e-10)',
    {
      SWIR1: image.select('SWIR1'),
      NIR: image.select('NIR')
    }
  ).rename('UI');

  return image
    .addBands(ndvi)
    .addBands(ndbi)
    .addBands(mndwi)
    .addBands(bsi)
    .addBands(ui);
}

var finalBands = [
  'BLUE', 'GREEN', 'RED', 'NIR', 'SWIR1', 'SWIR2',
  'NDVI', 'NDBI', 'MNDWI', 'BSI', 'UI'
];


// =============================================================
// Step 6: Binary classification function
// =============================================================

function classifyBinaryYear(year, trainingSamples) {
  var scale = 30;

  var composite = getYearComposite(year);
  var imageWithIndices = addIndices(composite);

  Map.addLayer(
    imageWithIndices,
    {min: 0.03, max: 0.30, bands: ['RED', 'GREEN', 'BLUE']},
    'RGB ' + year,
    false
  );

  var samples = imageWithIndices.select(finalBands).sampleRegions({
    collection: trainingSamples,
    properties: ['class'],
    scale: scale,
    geometries: false
  });

  print('Sample count ' + year, samples.size());

  var withRand = samples.randomColumn('rand', 42);
  var trainFC = withRand.filter(ee.Filter.lt('rand', 0.7));
  var validFC = withRand.filter(ee.Filter.gte('rand', 0.7));

  var clf = ee.Classifier.smileRandomForest({
    numberOfTrees: 200,
    variablesPerSplit: null,
    minLeafPopulation: 1,
    bagFraction: 0.7,
    seed: 42
  }).train({
    features: trainFC,
    classProperty: 'class',
    inputProperties: finalBands
  });

  var classified = imageWithIndices.select(finalBands).classify(clf);

  var classifiedSmooth = classified.focalMode({
    radius: 1,
    units: 'pixels'
  }).rename('classification');

  var validated = validFC.classify(clf);
  var cm = validated.errorMatrix('class', 'classification');

  print('==============================');
  print('Year:', year);
  print('Confusion Matrix:', cm);
  print('Overall Accuracy:', cm.accuracy());
  print('Kappa:', cm.kappa());

  Map.addLayer(
    classifiedSmooth,
    {min: 0, max: 1, palette: ['lightgray', 'blue']},
    'Classified ' + year,
    false
  );

  var warehouseFinal = classifiedSmooth.eq(1).rename('warehouse');

  Map.addLayer(
    warehouseFinal.selfMask(),
    {palette: ['blue']},
    'Warehouse ' + year,
    true
  );

  var areaDict = ee.Image.pixelArea()
    .updateMask(warehouseFinal)
    .rename('area')
    .reduceRegion({
      reducer: ee.Reducer.sum(),
      geometry: combinedAOI,
      scale: scale,
      maxPixels: 1e13
    });

  var areaSqKm = ee.Number(areaDict.get('area')).divide(1e6);
  print('Warehouse area ' + year + ' sq km:', areaSqKm);

  Export.image.toDrive({
    image: warehouseFinal.toByte(),
    description: 'warehouse_' + year + '_landsat30m',
    fileNamePrefix: 'warehouse_' + year + '_landsat30m',
    folder: 'GEE_exports',
    region: combinedAOI,
    scale: scale,
    maxPixels: 1e13
  });

  return warehouseFinal;
}


// =============================================================
// Step 7: Run all years
// =============================================================

var warehouseMask2010 = classifyBinaryYear(2010, training2010);
var warehouseMask2015 = classifyBinaryYear(2015, training2015);
var warehouseMask2020 = classifyBinaryYear(2020, training2020);
var warehouseMask2025 = classifyBinaryYear(2025, training2025);


// =============================================================
// Step 8: Change maps
// =============================================================

function makeChangeMap(oldMask, newMask, label) {
  oldMask = oldMask.unmask(0);
  newMask = newMask.unmask(0);

  var change = oldMask.multiply(2).add(newMask).rename('change');

  var remapped = change.remap(
    [0, 1, 2, 3],
    [0, 2, 1, 3]
  ).rename('change');

  Map.addLayer(
    remapped,
    {
      min: 0,
      max: 3,
      palette: [
        'd9d9d9',
        'f4b400',
        'd73027',
        '225ea8'
      ]
    },
    'Change ' + label,
    true
  );

  Export.image.toDrive({
    image: remapped.toByte(),
    description: 'warehouse_change_' + label + '_landsat30m',
    fileNamePrefix: 'warehouse_change_' + label + '_landsat30m',
    folder: 'GEE_exports',
    region: combinedAOI,
    scale: 30,
    maxPixels: 1e13
  });

  return remapped;
}

var change2010_2015 = makeChangeMap(warehouseMask2010, warehouseMask2015, '2010_2015');
var change2015_2020 = makeChangeMap(warehouseMask2015, warehouseMask2020, '2015_2020');
var change2020_2025 = makeChangeMap(warehouseMask2020, warehouseMask2025, '2020_2025');


// =============================================================
// Step 9: Area statistics
// =============================================================

function calcWarehouseArea(mask, year) {
  var areaDict = ee.Image.pixelArea()
    .updateMask(mask)
    .rename('area')
    .reduceRegion({
      reducer: ee.Reducer.sum(),
      geometry: combinedAOI,
      scale: 30,
      maxPixels: 1e13
    });

  return ee.Feature(null, {
    year: String(year),
    area_sqkm: ee.Number(areaDict.get('area')).divide(1e6)
  });
}

var areaFeatures = ee.FeatureCollection([
  calcWarehouseArea(warehouseMask2010, 2010),
  calcWarehouseArea(warehouseMask2015, 2015),
  calcWarehouseArea(warehouseMask2020, 2020),
  calcWarehouseArea(warehouseMask2025, 2025)
]);

print('Warehouse area by year', areaFeatures);

var areaChart = ui.Chart.feature.byFeature({
  features: areaFeatures,
  xProperty: 'year',
  yProperties: ['area_sqkm']
})
.setChartType('ColumnChart')
.setOptions({
  title: 'Warehouse Area by Year, Landsat 30 m',
  hAxis: {title: 'Year'},
  vAxis: {title: 'Warehouse Area sq km'},
  legend: {position: 'none'},
  colors: ['#2b83ba']
});

print(areaChart);


// =============================================================
// Step 10: Change statistics
// =============================================================

function calcChangeStats(changeImage, label) {
  function areaForClass(classValue) {
    var area = ee.Image.pixelArea()
      .updateMask(changeImage.eq(classValue))
      .rename('area')
      .reduceRegion({
        reducer: ee.Reducer.sum(),
        geometry: combinedAOI,
        scale: 30,
        maxPixels: 1e13
      });

    return ee.Number(area.get('area')).divide(1e6);
  }

  return ee.Feature(null, {
    period: label,
    lost_sqkm: areaForClass(1),
    new_sqkm: areaForClass(2),
    persistent_sqkm: areaForClass(3)
  });
}

var changeStats = ee.FeatureCollection([
  calcChangeStats(change2010_2015, '2010-2015'),
  calcChangeStats(change2015_2020, '2015-2020'),
  calcChangeStats(change2020_2025, '2020-2025')
]);

print('Change statistics by period', changeStats);

var changeChart = ui.Chart.feature.byFeature({
  features: changeStats,
  xProperty: 'period',
  yProperties: ['new_sqkm', 'lost_sqkm', 'persistent_sqkm']
})
.setChartType('ColumnChart')
.setOptions({
  title: 'Warehouse Change by Period, Landsat 30 m',
  hAxis: {title: 'Period'},
  vAxis: {title: 'Area sq km'},
  series: {
    0: {color: '#d73027'},
    1: {color: '#f4b400'},
    2: {color: '#225ea8'}
  }
});

print(changeChart);


// =============================================================
// Step 11: Export tables
// =============================================================

Export.table.toDrive({
  collection: areaFeatures,
  description: 'warehouse_area_by_year_landsat30m',
  fileFormat: 'CSV'
});

Export.table.toDrive({
  collection: changeStats,
  description: 'warehouse_change_stats_by_period_landsat30m',
  fileFormat: 'CSV'
});


// =============================================================
// Step 12: Legend
// =============================================================

var legend = ui.Panel({
  style: {
    position: 'bottom-left',
    padding: '8px 15px',
    backgroundColor: 'white'
  }
});

legend.add(ui.Label({
  value: 'Change Map Legend',
  style: {
    fontWeight: 'bold',
    fontSize: '14px',
    margin: '0 0 6px 0'
  }
}));

function makeLegendRow(color, name) {
  var colorBox = ui.Label({
    style: {
      backgroundColor: '#' + color,
      padding: '8px',
      margin: '0 0 4px 0'
    }
  });

  var description = ui.Label({
    value: name,
    style: {
      margin: '0 0 4px 6px'
    }
  });

  return ui.Panel({
    widgets: [colorBox, description],
    layout: ui.Panel.Layout.Flow('horizontal')
  });
}

legend.add(makeLegendRow('d9d9d9', 'No warehouse in both years'));
legend.add(makeLegendRow('f4b400', 'Lost warehouse'));
legend.add(makeLegendRow('d73027', 'New warehouse'));
legend.add(makeLegendRow('225ea8', 'Persistent warehouse'));

Map.add(legend);