async page => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error') errors.push(message.text());
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('http://127.0.0.1:8000', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.__SCENE_READY__ === true, { timeout: 180000 });
  await page.screenshot({ path: '/mnt/agents/output/app/src/web_desktop.png' });
  const stats = await page.evaluate(() => ({ model: window.__MODEL_STATS__, render: window.__RENDER_STATS__ }));
  await page.click('[data-view="face"]');
  await page.waitForTimeout(350);
  await page.screenshot({ path: '/mnt/agents/output/app/src/web_face.png' });
  await page.click('#motion');
  await page.waitForTimeout(1400);
  await page.screenshot({ path: '/mnt/agents/output/app/src/web_motion.png' });
  await page.click('#motion');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.click('#reset');
  await page.waitForTimeout(350);
  await page.screenshot({ path: '/mnt/agents/output/app/src/web_mobile.png' });
  return { stats, errors };
}
