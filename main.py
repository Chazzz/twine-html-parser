class Tiddler(object):
  def __init__(self, attrs, data):
    self.attrs = attrs
    self.data = data
    self.name = self.get_name(attrs)
  
  def get_name(self, attrs):
    for k, v in attrs:
      if k == "tiddler":
        return v
  
  def __repr__(self):
    return "<%s, %s>" % (self.name, self.data)

class TiddlerImage(Tiddler):
  def __init__(self, *args):
    super(TiddlerImage, self).__init__(*args)
  
  def __repr__(self):
    return "<%s, %s>" % (self.name, "<image data>")

class TiddlerStylesheet(Tiddler):
  def __init__(self, attrs, data):
    super(TiddlerStylesheet, self).__init__(attrs, data)
    self.stylesheet_name = self.get_stylesheet_name(attrs)
    self.images = self.process_stylesheet_data(data)
  
  def get_stylesheet_name(self, attrs):
    for k, v in attrs:
      if k == "tags":
        if len(v.split(" ")) == 1:
          return ""
        else:
          return v.split(" ")[1]

  def process_stylesheet_data(self, data):
    img_names = []
    split_text = data.split("[")
    for i, text in enumerate(split_text[:-1]):
      if text == "img":
        if "]]" not in split_text[i+1]:
          print("BAD IMG EMBED", data)
        else:
          img_names.append(split_text[i+1].split("]]")[0])

    return img_names

  def __repr__(self):
    return "<%s, %s>" % (self.name, self.images)
  
  def is_stylesheet(attrs):
    #[True for k, v in attrs if (k =="tags" and v != "" and v.split(" ")[0] == "stylesheet")]
    for k, v in attrs:
      if k == "tags":
        if v != "" and v.split(" ")[0] == "stylesheet":
          return True
    return False

class TiddlerText(Tiddler):
  def __init__(self, attrs, data):
    super(TiddlerText, self).__init__(attrs, data)
    self.stylesheets = self.get_inherited_stylesheets(attrs)
    self.images = TiddlerStylesheet(attrs, data).process_stylesheet_data(data)
    self.text_split, self.effects = self.process_text_data(data)
    self.choices = self.get_choices_from_text_split(self.text_split)
    # print(self.text_split)
    # print(self.choices)
    # print(self.stylesheets)

  def get_inherited_stylesheets(self, attrs):
    for k, v in attrs:
      if k == "tags":
        return v.split(" ")

  def process_text_data(self, data):
    split_text = data.split("<<")
    unmerged_text = [((), split_text[0])]
    effects = []
    conditionals = []
    for text in split_text[1:]:
      if ">>" not in text:
        print("BAD DATA (hanging <<):", data)
      else:
        split_text_2 = text.split(">>")
        ifsplit = split_text_2[0].split(" ")
        
        if len(ifsplit) >= 2 and ifsplit[0] == "if":
          conditionals.append((" ".join(ifsplit[1:]), True))
        elif len(ifsplit) >= 2 and ifsplit[0] == "elseif":
          conditionals[-1] = (conditionals[-1][0], False)
          conditionals.append("elseif")
          conditionals.append((" ".join(ifsplit[1:]), True))
        elif split_text_2[0] == "else":
          conditionals[-1] = (conditionals[-1][0], False)
        elif split_text_2[0] == "endif":
          #print(conditionals)
          if len(conditionals) == 0:
            print(data)
          conditionals.pop()
          #print("post pop", conditionals)
          while conditionals and conditionals[-1] in ["elseif"]:
            conditionals.pop()
            conditionals.pop()
        else:
          #print(split_text_2)
          effects.append((self.cleaned_conditionals(conditionals), split_text_2[0]))
        unmerged_text.append((self.cleaned_conditionals(conditionals), split_text_2[1]))
    #print(unmerged_text)
    # print(effects)
    return tuple(unmerged_text), tuple(effects)

  def cleaned_conditionals(self, conditionals):
    res_list = []
    for conditional in conditionals:
      if conditional not in ["elseif"]:
        res_list.append(conditional)
    return tuple(res_list)

  def get_choices_from_text_split(self, text_split):
    choices = []
    for conditionals, text in text_split:
      if "[[" not in text:
        continue
      else:
        pre_split, text_split_2 = text.split("[[", 1)
        if "]]" not in text_split_2:
          print("BAD DATA (hanging [[):", text)
        else:
          choice_text_dest, text_split_3 = text_split_2.split("]]", 1)
          if "|" in choice_text_dest:
            choice_text, choice_dest_and_effects = choice_text_dest.split("|", 1)
            if "][" in choice_dest_and_effects:
              choice_dest_split = choice_dest_and_effects.split("][")
              choice_dest = choice_dest_split[0]
              choice_effects = choice_dest_split[1:]
            else:
              choice_dest = choice_dest_and_effects
              choice_effects = []
          else: #label is same as displayed text
            if "][" in choice_text_dest:
              choice_dest_split = choice_text_dest.split("][")
              choice_text = choice_dest_split[0]
              choice_dest = choice_dest_split[0]
              choice_effects = choice_dest_split[1:]
            else:
              choice_text = choice_text_dest
              choice_dest = choice_text_dest
              choice_effects = []
          choices.append((conditionals, (choice_text, choice_dest, choice_effects)))
          choices += self.get_choices_from_text_split(((conditionals, text_split_3),))
    return choices

from html.parser import HTMLParser

# assumes parse is given a list of divs in string form
class MyHTMLParser(HTMLParser):
  def __init__(self):
    super(MyHTMLParser, self).__init__()
    self.tiddler_divs = []
    self.empty_divs_allowed = 1
    self.empty_divs_found = 0
    self.reset_current_div()

  def reset_current_div(self):
    self.current_div_attrs = ()
    self.current_div_data = ''

  def handle_starttag(self, tag, attrs):
    self.current_div_attrs = attrs

  def handle_endtag(self, tag):
    if [True for k, v in self.current_div_attrs if k == "tiddler"]:
      self.tiddler_divs.append((self.current_div_attrs,
                                self.current_div_data))
    else:
      self.empty_divs_found += 1
      if self.empty_divs_found > self.empty_divs_allowed:
        print("have some problems recording data", self.current_div_attrs, self.current_div_data)
    self.reset_current_div()    

  def handle_data(self, data):
    #print("Encountered some data  :", data)
    self.current_div_data = data
  
  def postprocess_tiddler(self):
    res = {}
    for attrs, data in self.tiddler_divs:
      if [True for k, v in attrs if (k, v) == ("tags", "Twine.image")]:
        tiddler = TiddlerImage(attrs, data)
      elif TiddlerStylesheet.is_stylesheet(attrs):
        tiddler = TiddlerStylesheet(attrs, data)
      else:
        tiddler = TiddlerText(attrs, data)
      if tiddler.name in res:
        print("ERROR (duplicate tiddler):", tiddler.name)
      res[tiddler.name] = tiddler

    return res

def graphify_tiddlers(tiddlers):
  stylesheet_lookup = {}
  for name, tiddler in tiddlers.items():
    if type(tiddler) == TiddlerStylesheet:
      stylesheet_lookup[tiddler.stylesheet_name] = tiddler.name
  for name, tiddler in tiddlers.items():
    tiddler.indegrees = set()
    tiddler.outdegrees = set()
  for name, tiddler in tiddlers.items():
    if type(tiddler) == TiddlerImage:
      continue
    if type(tiddler) in [TiddlerStylesheet, TiddlerText]:
      for image in tiddler.images:
        if image not in tiddlers:
          print("WARNING (image referenced but not found):", image)
        else:
          tiddler.outdegrees.add(image)
    if type(tiddler) == TiddlerText:
      for stylesheet in tiddler.stylesheets:
        if stylesheet not in ["bookmark", "script"]: #protected twine tags
          if stylesheet not in stylesheet_lookup:
            print("WARNING (broken, useless and/or unregistered tag):", stylesheet)
          else:
            tiddler.outdegrees.add(stylesheet_lookup[stylesheet])
      for cond, choice_tuple in tiddler.choices:
        text, dest, effects = choice_tuple
        if dest not in ["previous()"]:
          if dest not in tiddlers:
            print("WARNING (choice destination not found):", dest)
          else:
            tiddler.outdegrees.add(dest)
      for conds, effect in tiddler.effects:
        if effect.startswith("display "):
          dest = effect.split(" ", 1)[1]
          if dest not in tiddlers:
            print("WARNING (display destination not found):", dest)
          else:
            tiddler.outdegrees.add(dest)
  for name, tiddler in tiddlers.items():
    for outdegree in tiddler.outdegrees:
      tiddlers[outdegree].indegrees.add(name)
  for name, tiddler in tiddlers.items():
    if tiddler.indegrees == set():
      print("Origin found:", name)

def sort_outdegrees_depth(outdegrees, tiddler_depths):
  def tiddler_depth(name):
    return len(tiddler_depths[name])
  outdegrees.sort(key = tiddler_depth, reverse = True)

def tiddlers_smart_topological_sort(tiddlers):
  # Approximate topological sort, preferring to list smaller branches before larger branches
  # Loops are "ignored" by detecting the loop and not recursing deeper
  # Some extremely interwoven graphs may not render desirably (additional heuristics may need to be added).
  # Stylesheets and images are not recursed into, on the basis that they are resusable.
  tiddler_depths = {}
  visited_tiddlers = []
  # First, estimate the size of each tiddler's branch (for sorting)
  for name, tiddler in tiddlers.items():
    if tiddler.indegrees == set():
      estimate_branch_size_recursive(tiddlers, name, tiddler_depths, visited_tiddlers)
  # Second, topological sort using branch size to determine ordering
  sort_res = []
  visited_tiddlers_2 = []
  insert_order = []
  origins = [name for name in tiddlers if tiddlers[name].indegrees == set()]
  sort_outdegrees_depth(origins, tiddler_depths)
  for origin in origins:
    recursive_smart_topological_sort(tiddlers, origin, tiddler_depths, visited_tiddlers_2, sort_res)
  return sort_res

def recursive_smart_topological_sort(tiddlers, name, tiddler_depths, visited_tiddlers, res):
  visited_tiddlers.append(name)
  traversible_outdegrees = [o for o in tiddlers[name].outdegrees if type(tiddlers[o]) == TiddlerText]
  sort_outdegrees_depth(traversible_outdegrees, tiddler_depths)
  for outdegree in traversible_outdegrees:
    if outdegree not in visited_tiddlers:
      recursive_smart_topological_sort(tiddlers, outdegree, tiddler_depths, visited_tiddlers, res)

  res.insert(0, name)

def estimate_branch_size_recursive(tiddlers, name, tiddler_depths, visited_tiddlers):
  visited_tiddlers.append(name)
  tiddler_depths[name] = set([name])
  traversible_outdegrees = [o for o in tiddlers[name].outdegrees if type(tiddlers[o]) == TiddlerText]
  for outdegree in traversible_outdegrees:
    if outdegree not in visited_tiddlers:
      estimate_branch_size_recursive(tiddlers, outdegree, tiddler_depths, visited_tiddlers)
  # print(name, [(outdegree, len(tiddler_depths[outdegree])) for outdegree in traversible_outdegrees])
  for outdegree in traversible_outdegrees:
    tiddler_depths[name] |= tiddler_depths[outdegree] # 1 if loop


import sys
# instantiate the parser and fed it some HTML
parser = MyHTMLParser()
with open(sys.argv[1]) as f:
  for line in f.readlines():
    if "tiddler=" in line:
      parser.feed(line)
tiddlers = parser.postprocess_tiddler()
graphify_tiddlers(tiddlers)
sorted_tiddlers = tiddlers_smart_topological_sort(tiddlers)
for name in sorted_tiddlers:
  print(name, len(tiddler_depths[name])) #TODO: Add pretty printing of tiddlers