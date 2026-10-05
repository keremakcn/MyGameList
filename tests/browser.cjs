const {chromium}=require(process.env.PLAYWRIGHT_MODULE);
const assert=require('node:assert/strict');
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.EDGE_PATH});
  const page=await browser.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const go=path=>page.goto('http://127.0.0.1:5064'+path);
  for(const width of [800,1100,1550]){
    await page.setViewportSize({width,height:900});
    for(const path of ['/','/settings','/search','/search?q=Portal','/search?q=offline','/search?q=nothing','/search?q=Valve&type=developers','/search?q=Valve&type=publishers','/game/123','/edit/125']){
      assert.equal((await go(path)).status(),200);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`${width}: ${path} overflow`);
    }
  }
  await go('/settings');
  assert.equal(await page.locator('input[name=api_key]').count(),0);
  await page.screenshot({path:'.qa/settings-desktop.png',fullPage:true});
  await go('/search?q=Portal');
  const card=page.locator('.game-card').filter({has:page.getByRole('heading',{name:'Portal',exact:true})});
  await card.getByRole('button',{name:'+ Add to Want to Play',exact:true}).click();
  await card.getByRole('button',{name:'✓ In your library',exact:true}).waitFor();
  assert.match(page.url(),/search\?q=Portal$/);
  assert(await card.getByRole('button',{name:'✓ In your library',exact:true}).isDisabled());
  await go('/edit/123');
  await page.locator('[name=status]').selectOption('Played');
  await page.locator('[name=my_rating]').fill('9');
  await page.locator('[name=note]').fill('Private desktop note.');
  await page.locator('[name=favorite]').check();
  await Promise.all([page.waitForNavigation(),page.getByRole('button',{name:'Save',exact:true}).click()]);
  await go('/edit/123');
  assert.equal(await page.locator('[name=note]').inputValue(),'Private desktop note.');
  assert.equal(await page.locator('[name=my_rating]').inputValue(),'9.0');
  assert(await page.locator('[name=favorite]').isChecked());
  await go('/search?q=Valve&type=developers');
  await page.locator('.game-card').first().click();
  await page.waitForURL('**/search?**company=1**');
  assert.equal(await page.locator('.game-card').count(),3);
  await go('/search');
  const input=page.locator('.discovery-search [name=q]');
  await input.fill('Portal');
  await page.locator('.suggestion-list [role=option]').first().waitFor();
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('Enter');
  await page.waitForURL('**/game/123?**');
  await go('/set-language/tr');
  await go('/settings');
  assert.equal(await page.getByRole('heading',{name:'Keşfetmeye hazırsın'}).count(),1);
  await page.screenshot({path:'.qa/settings-desktop-tr.png',fullPage:true});
  await go('/');
  await page.screenshot({path:'.qa/library-desktop.png',fullPage:true});
  assert.deepEqual(errors,[]);
  await browser.close();
  console.log('30 desktop page/layout checks plus key-free bilingual settings, quick-add, journal, favorites, developer navigation and keyboard suggestions passed.');
})().catch(e=>{console.error(e);process.exit(1)});
